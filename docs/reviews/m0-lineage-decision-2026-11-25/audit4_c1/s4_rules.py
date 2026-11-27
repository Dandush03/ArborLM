# ruff: noqa
"""Audit 4 (C1), step 4a: per item, from the rendered SOURCE only (stdlib; imports nothing from studies/), a shape label and three kinds of
predictions:  F.* closed forms (answer without tracing the program's loop-carried state: a formula, a library call, reading a literal),
S.* cheap shortcuts (often a MUTATED copy of the program, e.g. a step dropped, run in-process under a 2 s alarm), G.* generic literal rules.
Helpers for parsing are adapted from audit3_c1/a3_shortcuts.py (the predecessor's, reused as allowed); the rules are mine.
Usage:  python s4_rules.py GEN_DIR OUT_JSONL_GZ   (writes one record per item)
"""
import ast, bisect, contextlib, gzip, glob, io, json, math, os, re, signal, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor


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


def top_sets(tree):
    return [(n.targets[0].id, n.value) for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)]


def print_arg(tree):
    return tree.body[-1].value.args[0]


def print_name(tree):
    a = print_arg(tree)
    return a.id if isinstance(a, ast.Name) else None


def range_args(tree):
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "range":
            out.append((n.lineno, n.col_offset, [lit(a) for a in n.args]))
    out.sort()
    return [x[2] for x in out]


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


def mrun(src, subs, count=0, must_change=True):
    """Run src after regex substitutions [(pat, repl, flags)]; None if nothing changed (rule does not apply) or the run fails."""
    s2 = src
    for pat, rep in subs:
        s2 = re.sub(pat, rep, s2, count=count, flags=re.M)
    if must_change and s2 == src:
        return None
    return run_src(s2)


def digits(x, base):
    d = []
    while x:
        d.append(x % base)
        x //= base
    return d


def isprime(k):
    return k >= 2 and all(k % d for d in range(2, int(k ** 0.5) + 1))


def ap_count_sum(start, step, n, m, rem, eq):
    """Closed form: count and sum of i = start + step*t, 0 <= t < n, with (i % m == rem) == eq. Uses arithmetic progressions only
    (the residue classes of t modulo the period, at most m <= 5 of them; no loop over the range)."""
    p = m // math.gcd(step, m)
    cnt_q = sum_q = 0
    for r0 in range(p):
        if ((start + step * r0) % m == rem) != eq:
            continue
        if r0 >= n:
            continue
        k = (n - 1 - r0) // p + 1  # t = r0, r0+p, ..., count k
        ts = k * r0 + p * k * (k - 1) // 2
        cnt_q += k
        sum_q += start * k + step * ts
    return cnt_q, sum_q


def bfs(adj, start):
    dist = [-1] * len(adj)
    dist[start] = 0
    q = [start]
    for u in q:
        for v in adj[u]:
            if dist[v] == -1:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist, q


# ------------------------------------------------------------------ lineage-specific
def specific(lid, src, tree):  # noqa: C901
    L = {}
    ints = ints_in_order(tree)
    lists = int_lists(tree)
    ss = strs(tree)
    ts = top_sets(tree)
    pn = print_name(tree)
    lines = src.strip().splitlines()
    last = lines[-1]
    sh = None
    n = lid.replace("C1.", "")
    if n == "while_counter_f3":
        if re.search(r"while \w+ != 1:", src):
            sh = "collatz"
            # other order of the add and the update
            if re.search(r"^    \w+ \+= \w+\n    if", src, re.M):
                L["S.other_order"] = mrun(src, [(r"^    (\w+ \+= \w+)\n((?:    .*\n)+?)(?=print)", r"\2    \1\n")])
            else:
                L["S.other_order"] = mrun(src, [(r"^((?:    (?!\w+ \+= ).*\n)+)(    \w+ \+= \w+\n)", r"\2\1")])
            x0 = ints[0]
            L["S.x0_times_steps"] = None
        elif re.search(r"while \w+ < \d+:", src):
            sh = "grow"
            L["S.no_mod_term"] = mrun(src, [(r" \+ \w+ % \d+", "")])
            L["S.threshold"] = re.search(r"while \w+ < (\d+):", src).group(1)
        else:
            sh = "down"
            L["S.sum_before_step"] = mrun(src, [(r"^(    if .*\n(?:        .*\n|    else:\n)+)(    \w+ \+= \w+\n)", r"\2\1")])
            L["S.no_halving"] = mrun(src, [(r"(\w+) = \w+ // 2", r"\1 = \1")])
    elif n == "euclid_gcd_traced_f3":
        x, y = ints[0], ints[1]
        R = int(re.search(r"and \w+ < (\d+):", src).group(1))
        p, q, st, rems = x, y, [], []
        while q:
            p, q = q, p % q
            st.append((p, q))
            rems.append(q)
        if "' '" in last:
            sh = "state"
            L["S.one_more_round"] = f"{st[R][0]} {st[R][1]}" if R < len(st) else None
            L["S.one_less_round"] = f"{st[R-2][0]} {st[R-2][1]}" if R >= 2 else f"{x} {y}"
            L["S.gcd_0"] = f"{math.gcd(x, y)} 0"
        else:
            sh = "rsum"
            L["S.unweighted_R"] = str(sum(rems[:R]))
            L["S.weight_k"] = str(sum((k + 1) * rems[k] for k in range(R)))
            L["S.all_rounds_weighted"] = str(sum((k + 2) * rems[k] for k in range(len(rems))))
            L["S.all_rems"] = str(sum(rems))
            L["S.literal_y"] = str(y)
    elif n == "cond_chain_f3":
        aug = re.search(r"^    (\w+) \+= (.*)$", src, re.M)
        names = [nm for nm, _ in ts]
        a_nm, b_nm = names[0], names[1]
        e = aug.group(2)
        sh = "a" if e == a_nm else ("b" if e == b_nm else "a-b")
        # rounds times the final value of the printed expression
        rounds = range_args(tree)[0][0]
        L["S.rounds_x_final"] = mrun(src, [(r"^    \w+ \+= .*\n", ""), (r"^print\(\w+\)$", f"print({rounds} * ({e}))")])
        L["S.no_halving"] = mrun(src, [(r"^    if \w+ \+ \w+ > \d+:\n        \w+ = \w+ // 2\n", "")])
        g = math.gcd(ints[0], ints[1])
        L["S.rounds_x_gcd"] = str(rounds * g)
    elif n == "fast_power_f3":
        names = [nm for nm, _ in ts]
        vals = {nm: lit(v) for nm, v in ts}
        res, b, e, m = names[0], names[1], names[2], names[3]
        B0, E0, M0 = vals[b], vals[e], vals[m]
        bl = E0.bit_length()
        sh = "res" if pn == res else ("base" if pn == b else "bsum")
        L["F.pow_res"] = str(pow(B0, E0, M0)) if sh == "res" else None
        L["F.pow_base"] = str(pow(B0, 2 ** bl, M0)) if sh == "base" else None
        L["F.pow_bsum"] = str(sum(pow(B0, 2 ** k, M0) for k in range(bl))) if sh == "bsum" else None
        L["S.drop_c"] = mrun(src, [(r"\(\w+ \* \w+ \+ \d+\) %", lambda mm: mm.group(0).split(" + ")[0] + ") %")])
        L["S.literal_base"] = str(B0) if sh == "base" else None
    elif n == "digit_peel_f3":
        x = ints[0]
        base = int(re.search(r"= \w+ % (\d+)\n", src).group(1))
        ds = digits(x, base)  # least significant first
        dd = [int(c) for c in str(x)][::-1]
        if "* " in src and re.search(r"= \w+ \* (\d+) \+ \w+", src):
            sh = "fold"
            k = int(re.search(r"= \w+ \* (\d+) \+ \w+", src).group(1))
            fold = lambda seq: (lambda acc=[0]: [acc.__setitem__(0, acc[0] * k + d) for d in seq] and acc[0])()
            L["S.decimal_digits_fold"] = str(fold(dd))
            L["S.msd_first_fold"] = str(fold(ds[::-1]))
            L["S.k_eq_base_reverse"] = str(fold(ds)) if k == base else None  # (= the answer when k == base: digit reversal; needs the digits)
            sh += "_k=base" if k == base else ""
        else:
            sh = "wsum"
            L["S.decimal_digits_wsum"] = str(sum(d * (i + 1) for i, d in enumerate(dd)))
            L["S.msd_first_wsum"] = str(sum(d * (i + 1) for i, d in enumerate(ds[::-1])))
            L["S.digit_sum"] = str(sum(ds))
    elif n == "partition_pass_f3":
        vals = lists[0]
        m1 = range_args(tree)[0][0]  # for j in range(m - 1)
        op = re.search(r"if \w+\[\w+\] (<=|<) \w+:", src).group(1)
        f = (lambda a, b: a <= b) if op == "<=" else (lambda a, b: a < b)
        piv = vals[m1]
        smalls = [p for p in range(m1) if f(vals[p], piv)]
        if pn and ("+= " in src and re.search(r"^        \w+ \+= \w+\[\w+\]$", src, re.M)):
            sh = "disp"
        elif re.search(r"\[\w+ \+ 1\] = \w+", src):
            sh = "list"
        else:
            sh = "mid"
        lo = [v for v in vals[:m1] if f(v, piv)]
        hi = [v for v in vals[:m1] if not f(v, piv)]
        if sh == "disp":
            L["F.2x0_plus_x1"] = str(2 * vals[0] + vals[1])
            L["S.sum_first3"] = str(vals[0] + vals[1] + vals[2])
        else:
            out = list(vals)
            if len(smalls) == 3:
                for k, p in enumerate(smalls):
                    out[k] = vals[p]
                out[smalls[1]] = vals[1]
                out[smalls[2]] = vals[0]
                if sh == "list":
                    out[3], out[m1] = piv, vals[3]
            L["F.template_permutation"] = str(out) if len(smalls) == 3 else None
            L["S.stable_partition"] = str(lo + ([piv] + hi if sh == "list" else hi + [piv]) + vals[m1 + 1:])
            L["S.sorted_prefix"] = str(sorted(vals[: m1 + 1]) + vals[m1 + 1:])
            L["S.echo"] = str(vals)
        L["X.n_smalls"] = str(len(smalls))
    elif n == "merge_two_sorted_f3":
        a, b = lists[0], lists[1]
        sh = "diffsum" if re.search(r"\+= \w+\[\w+\] - \w+\[\w+\]", src) else "maxsum"
        if sh == "diffsum":
            L["S.suma_minus_sumb"] = str(sum(a) - sum(b))
            L["S.zero"] = "0"
        else:
            L["S.sum_all"] = str(sum(a) + sum(b))
            L["S.sum_all_minus_min"] = str(sum(a) + sum(b) - min(a[0], b[0]))
            L["S.sum_merged_but_last"] = str(sum(sorted(a + b)[1:]) - max(a[-1], b[-1]))
    elif n == "sieve_marking_f3":
        fl = lists[0]
        sh = "strikesum" if re.search(r"^            \w+ \+= \w+$", src, re.M) else "flags"
        L["S.all_ones_start"] = run_src(src.replace(str(fl), str([1] * len(fl)), 1))
        # strike from every index flagged in the INPUT (ignore that earlier passes clear flags)
        fl_nm = ts[0][0]
        L["S.use_initial_flags"] = mrun(src, [(rf"^({fl_nm} = .*)$", rf"\1\n__init = list({fl_nm})"), (rf"if {fl_nm}\[(\w+)\] == 1:", r"if __init[\1] == 1:")], count=1)
        if sh == "flags":
            L["S.echo"] = str(fl)
            L["S.primes_only"] = str([1 if (fl[k] == 1 and (k < 2 or isprime(k))) else 0 for k in range(len(fl))])
    elif n == "binary_search_f3":
        vals = lists[0]
        t = ints[len(vals)]
        closed = "<=" in re.search(r"while (.*):", src).group(1)
        if "''" in src and "','" in src:
            sh = "probes"
        elif "''" in src:
            sh = "path"
        else:
            sh = "sum"
        sh += "_closed" if closed else "_half"
        L["X.present"] = str(t in vals)
        L["X.n"] = str(len(vals))
    elif n == "majority_vote_scan_f3":
        vals = lists[0]
        body = src.split("for ")[1]
        if re.search(r"= 1\n        \w+ \+= \w+\n", src):
            sh = "repl"
            L["S.first_elem"] = str(vals[0])
            L["S.sum_distinct"] = str(sum(set(vals)))
        elif re.search(r"^    \w+ \+= (\w+)$", src, re.M):
            v = re.search(r"^    \w+ \+= (\w+)$", src, re.M).group(1)
            cnt_nm = ts[2][0]
            sh = "cntsum" if v == cnt_nm else "candsum"
            if sh == "candsum":
                L["S.prefix_mode_sum"] = str(sum(Counter(vals[: i + 1]).most_common(1)[0][0] for i in range(len(vals))))
                L["S.sum_vals"] = str(sum(vals))
        L["S.mode"] = str(Counter(vals).most_common(1)[0][0])
    elif n == "counter_list_f3":
        vals, k = lists[0], len(lists[1])
        c = [0] * k
        for v in vals:
            c[v % k] += 1
        L["F.residue_histogram"] = str(c)
        st, c2 = 0, [0] * k
        for v in vals:
            st = (st + v) % k
            c2[st] += 1
        L["S.prefix_sum_histogram"] = str(c2)
        sty = "plain" if "if " not in src.split("for ")[1] else ("parity" if "% 2 == 0" in src else "threshold")
        sh = f"style_{sty}"
    elif n == "list_build_f3":
        sh = "sum" if "sum(" in last else ("list" if re.match(r"print\(\w+\)$", last) and "+= " not in src else "wsum")
        L["S.no_filter"] = mrun(src, [(r"^    if \w+ % \d+ != \d+:\n        (\w+\.append\(.*\))$", r"    \1")])
        sh += "_filt" if "!=" in src else ""
    elif n == "nested_pairs_f3":
        tri = re.search(r"for \w+ in range\((\w+)\):\n\s+if", src)
        sh = "tri" if tri and not tri.group(1).isdigit() else "rect"
        L["S.no_condition"] = mrun(src, [(r"^        if .*:\n            (\w+ \+= .*)$", r"        \1")])
        L["S.count_only"] = mrun(src, [(r"^(            \w+) \+= .*$", r"\1 += 1")])
    elif n == "coin_change_table_f3":
        cv = lists[0]
        T = int(re.search(r"print\(\w+\[(\d+)\]\)", last).group(1)) if re.search(r"print\(\w+\[(\d+)\]\)", last) else None
        if "min(" in src:
            sh = "fewest"
            rem, cnt = T, 0
            for c in sorted(cv, reverse=True):
                cnt += rem // c
                rem %= c
            L["S.greedy"] = str(cnt) if rem == 0 else None
            L["S.T_div_maxcoin_ceil"] = str(-(-T // max(cv)))
        elif "sum(" in last:
            sh = "tablesum"
        elif re.search(r"for \w+ in range\(1, \d+\):\n    for", src):
            sh = "orders"
        else:
            sh = "combos"
        if T is not None and sh in ("orders", "combos"):
            ways_c = [1] + [0] * T
            for c in cv:
                for a in range(c, T + 1):
                    ways_c[a] += ways_c[a - c]
            ways_o = [1] + [0] * T
            for a in range(1, T + 1):
                ways_o[a] = sum(ways_o[a - c] for c in cv if a >= c)
            L["S.swap_combos_orders"] = str(ways_o[T] if sh == "combos" else ways_c[T])
    elif n == "bracket_matching_f3":
        s = ss[0]
        if "* 10" in last:
            sh = "code"
        elif "[0:" in last or "[:" in last:
            sh = "remain_at" if re.search(r"for \w+ in range\(\d+\):\n    \w+ = ", src) else "remain"
        else:
            # errpos: tot added in the else (fail) branch; popsum: in the hit branch
            sh = "errpos" if re.search(r"else:\n            \w+ \+= 1\n            \w+ \+= \w+", src) or re.search(r"^    else:\n        \w+ \+= 1\n        \w+ \+= \w+", src, re.M) else "popsum"
        L["S.pop_any_closer"] = mrun(src, [(r" and \w+\[\w+ - 1\] == \d+:", ":")])
        L["S.never_pop"] = mrun(src, [(r"if \w+ > 0 and \w+\[\w+ - 1\] == \d+:", "if False:"), (r"^    elif \w+ > 0 and \w+\[\w+ - 1\] == 4:", "    elif False:")])
        if sh == "errpos":
            L["S.sum_pos_all_closers"] = str(sum(i for i, c in enumerate(s) if c in ")]}>"))
    elif n == "union_find_links_f3":
        sh = "parents" if pn and re.match(r"print\(\w+\)$", last) and "+=" not in src else ("rootsum" if "find(" in src.split("\n")[-3] else "wsum")
        L["S.no_find"] = mrun(src, [(r"= find\((\w+), (\w+\[\w+\])\)", r"= \2")], count=2)
        L["S.flip_rule"] = mrun(src, [(r"^        (\w+)\[(\w+)\] = (\w+)$", r"        \1[\3] = \2")], count=1)
        L["S.identity"] = None
    elif n == "shared_lists_f3":
        sh = "sum" if "sum(" in last else "list"
        L["S.copy_on_alias"] = mrun(src, [(r"^(\w+) = (\w+)$", r"\1 = \2[:]")])
        L["S.bump_returns_copy"] = None
    elif n == "bytecode_loop_f3":
        code = lists[0]
        pnn = pn
        names = [nm for nm, _ in ts]
        sh = "acc" if pnn == names[2] else ("sumarg" if re.search(r"^    \w+ \+= \w+$", src, re.M) else "reg")
        L["S.no_skips"] = mrun(src, [(r"(if \w+ % 2 == \w+ % 2:\n\s+)(\w+) = \w+ \+ 2", r"\1\2 = \2")])
        L["S.always_skip"] = mrun(src, [(r"if \w+ % 2 == \w+ % 2:", "if True:")])
        L["S.sum_all_args"] = str(sum(code[1::2]))
    elif n == "turtle_walk_f3":
        sh = "pos" if "','" in last else "pathsum"
        L["S.no_turns"] = mrun(src, [(r"^(\s+)(\w+) = \(\w+ \+ \d\) % 4$", r"\1\2 = \2")])
        L["S.no_back"] = mrun(src, [(r"elif \w+ == 6:", "elif False:")])
        L["S.zero"] = "0,0" if sh == "pos" else "0"
    elif n == "cellular_update_f3":
        init = lists[0]
        sh = ("row" if re.match(r"print\(\w+\)$", last) and "+=" not in src else "weighted")
        sty = "table" if "[4 *" in src or "* 4 +" in src else ("equals" if re.search(r"\+ \w+ \+ \w+ == \d", src) else "branch")
        sh += "_" + sty
        L["S.echo_init"] = str(init) if sh.startswith("row") else str(sum(i * v for i, v in enumerate(init)))
        L["S.one_generation"] = mrun(src, [(r"^for (\w+) in range\(\d+\):", r"for \1 in range(1):")], count=1)
        L["S.swap_boundary"] = None
    elif n == "func_compose_f3":
        sh = "h" if len(re.findall(r"^def ", src, re.M)) == 3 else "g"
        sh += "_two" if re.search(r"\) [+-] \w+\(", last) else "_one"
        L["S.drop_outer_mod"] = mrun(src, [(r"^(    return \w+\(\w+\)) % \d+$", r"\1")])
        cs = src.replace("//", "__FD__")
        L["S.c_semantics"] = None
        if "//" in src or "%" in src:
            t2 = ast.parse(src)

            class T(ast.NodeTransformer):
                def visit_BinOp(self, nd):
                    self.generic_visit(nd)
                    if isinstance(nd.op, ast.FloorDiv):
                        return ast.Call(ast.Name("__tdiv", ast.Load()), [nd.left, nd.right], [])
                    if isinstance(nd.op, ast.Mod):
                        return ast.Call(ast.Name("__tmod", ast.Load()), [nd.left, nd.right], [])
                    return nd

            t2 = T().visit(t2)
            ast.fix_missing_locations(t2)
            pre = "def __tdiv(a, b):\n    q = abs(a) // abs(b)\n    return q if (a >= 0) == (b >= 0) else -q\ndef __tmod(a, b):\n    return a - b * __tdiv(a, b)\n"
            L["S.c_semantics"] = run_src(pre + ast.unparse(t2))
    elif n == "fib_like_f3":
        sh = "mod" if "%" in src else "plain"
        L["S.drop_mod"] = mrun(src, [(r"\) % \d+$", ")"), (r"^(    \w+ = )\((.*)\)$", r"\1\2")]) if "%" in src else None
        L["S.one_more_iter"] = mrun(src, [(r"in range\((\d+)\)", lambda mm: f"in range({int(mm.group(1)) + 1})")])
        L["S.one_less_iter"] = mrun(src, [(r"in range\((\d+)\)", lambda mm: f"in range({int(mm.group(1)) - 1})")])
    elif n == "fib_shapes_recursive_f3":
        sh = "tri" if "- 3)" in src else "two"
        L["S.arg_minus_1"] = mrun(src, [(r"^print\((\w+)\((\d+)\)\)$", lambda mm: f"print({mm.group(1)}({int(mm.group(2)) - 1}))")])
        L["S.arg_plus_1"] = mrun(src, [(r"^print\((\w+)\((\d+)\)\)$", lambda mm: f"print({mm.group(1)}({int(mm.group(2)) + 1}))")])
    elif n == "string_methods_f3":
        sh = "tail:" + (re.search(r"\.lower\(\)(.*)\)$", last).group(1) or "none")
        L["S.no_tail"] = mrun(src, [(r"\.lower\(\)\[.*\]\)$", ".lower())")])
        L["S.last_op_dropped"] = None
    elif n == "string_build_f3":
        sh = "rev" if "::(-1)]" in last or "::-1]" in last else ("alt" if "::2]" in last else "s")
        L["S.no_tail"] = mrun(src, [(r"^print\((\w+)\[.*\]\)$", r"print(\1)")])
        L["S.step1"] = mrun(src, [(r"in range\((\d+), (\d+), 2\)", r"in range(\1, \2)")])
    # ---------------- unchanged lineages (shape rules re-run)
    elif n == "bfs_queue":
        adj = [[lit(e) for e in row.elts] for row in ts[0][1].elts]
        start = lit([nd for nd in tree.body if isinstance(nd, ast.Assign) and isinstance(nd.targets[0], ast.Subscript)][0].value)
        sym = [sorted(set(adj[u]) | {v for v in range(len(adj)) if u in adj[v]}) for u in range(len(adj))]
        d_s, q_s = bfs([sorted(x) for x in adj], start)
        d_u, q_u = bfs(sym, start)
        if "[0:" in last:
            sh = "order"
            L["S.sorted_neighbours_order"] = str(q_s)
            L["S.undirected_order"] = str(q_u)
        elif re.search(r"print\(\w+\[\w+ - 1\]\)", last):
            sh = "last"
            L["S.sorted_neighbours_last"] = str(q_s[-1])
            L["S.max_node"] = str(len(adj) - 1)
        elif re.search(r"print\(\w+\[\d+\]\)", last):
            sh = "target"
            tgt = int(re.search(r"\[(\d+)\]", last).group(1))
            L["S.undirected_dist"] = str(d_u[tgt])
            L["S.one"] = "1"
            L["S.two"] = "2"
        else:
            sh = "distsum"
            L["S.undirected_distsum"] = str(sum(x for x in d_u if x > 0))
    elif n == "bubble_pass":
        vals = lists[0]
        npass = src.count("for ")
        desc = re.search(r"if \w+\[\w+\] (<|>) ", src).group(1) == "<"
        sh = f"passes{npass}"
        L["S.sorted"] = str(sorted(vals, reverse=desc))
        L["S.echo"] = str(vals)
        L["S.one_pass_only"] = mrun(src, [(r"((?:for .*\n(?:    .*\n)+))((?:for .*\n(?:    .*\n)+)+)", r"\1")]) if npass > 1 else None
        # max/min moved to the end only
        v2 = list(vals)
        ex = max(v2) if not desc else min(v2)
        v2.remove(ex)
        L["S.extreme_to_end"] = str(v2 + [ex])
    elif n == "circle_elimination_r2":
        sh = "survivor" if src.count("for ") >= 2 else ("sum" if re.search(r"^    \w+ \+= \w+$", src, re.M) else "last")
        fl = lists[0]
        L["S.ignore_dead_initial"] = run_src(src.replace(str(fl), str([1] * len(fl)), 1))
        L["S.start_at_0"] = mrun(src, [(r"^(\w+) = (\d+)$", lambda mm: f"{mm.group(1)} = {len(fl) - 1}")], count=1)
    elif n == "func_branch":
        sh = f"calls{last.count('(') - 1}" + ("_even" if "% 2 == 0" in src else "")
        L["S.drop_even_branch"] = mrun(src, [(r"^    elif \w+ % 2 == 0:\n        return .*\n", "")])
    elif n == "grid_path_table":
        g = [[lit(e) for e in row.elts] for row in ts[0][1].elts]
        R, Cc = len(g), len(g[0])
        sh = "count" if "== 0:" in src.split("for")[2] and "min(" not in src and "max(" not in src else ("max" if "max(" in src else "min")
        if sh == "count":
            L["S.binomial_no_blocks"] = str(math.comb(R + Cc - 2, R - 1))
        else:
            f = max if sh == "max" else min
            i = j = 0
            tot = g[0][0]
            while (i, j) != (R - 1, Cc - 1):
                if i == R - 1:
                    j += 1
                elif j == Cc - 1:
                    i += 1
                elif f(g[i + 1][j], g[i][j + 1]) == g[i + 1][j]:
                    i += 1
                else:
                    j += 1
                tot += g[i][j]
            L["S.greedy_path"] = str(tot)
    elif n == "loop_sum":
        acc0 = ints[0]
        ra = range_args(tree)[0]
        start, stop = ra[0], ra[1]
        step = ra[2] if len(ra) > 2 else 1
        mm = re.search(r"if \w+ % (\d+) (==|!=) (\d+):", src)
        m, eq, rem = int(mm.group(1)), mm.group(2) == "==", int(mm.group(3))
        aug = re.search(r"^        \w+ ([+-])= \w+ \* (\d+)$", src, re.M)
        sgn, c = (1 if aug.group(1) == "+" else -1), int(aug.group(2))
        els = re.search(r"else:\n        \w+ \+= (\d+)", src)
        k = int(els.group(1)) if els else 0
        N = len(range(start, stop, step))  # count of iterations from the literals (arithmetic, no loop)
        cq, sq = ap_count_sum(start, step, N, m, rem, eq)
        sh = "else" if els else "plain"
        L["F.arith_series"] = str(acc0 + sgn * c * sq + k * (N - cq))
    elif n == "mirror_pointers":
        s = ss[0]
        sh = "poss" if re.search(r"\+= \w+$", src, re.M) and "''" not in src else ("pairs" if re.search(r"\+ \w+\[\w+\] \+ \w+\[\w+\]", src) else "chars")
        nn = len(s)
        bad = [k for k in range(nn) if s[k] != s[nn - 1 - k]]  # whole string, both halves (overshoot)
        if sh == "poss":
            L["S.whole_string"] = str(sum(bad))
        elif sh == "chars":
            L["S.whole_string"] = "".join(s[k] for k in bad)
        else:
            L["S.whole_string"] = "".join(s[k] + s[nn - 1 - k] for k in bad)
    elif n == "postfix_evaluation":
        toks = lists[0]
        sh = "top" if re.search(r"print\(\w+\[\w+ - 1\]\)", last) else "opsum"
        L["S.sum_operands"] = str(sum(t for t in toks if t >= 0))
        L["S.last_operand"] = str([t for t in toks if t >= 0][-1])
    elif n == "recursive_calls_r2":
        sh = "listfold" if "len(" in src else ("mutual" if len(re.findall(r"^def ", src, re.M)) == 2 else "split")
        L["S.arg_minus_1"] = mrun(src, [(r"^print\((\w+)\((\d+)\)\)$", lambda mm: f"print({mm.group(1)}({int(mm.group(2)) - 1}))")])
    elif n == "run_length_scan":
        sh = "long" if ">= 2" in src else ("counts" if re.search(r"= \w+ \+ str\(\w+\)$", src, re.M) and not re.search(r"\+ \w+ \+ str", src) else "enc")
        L["S.no_final_close"] = mrun(src, [(r"\n(\w+ = \w+ \+ (?:\w+ \+ )?str\(\w+\))\n(print)", r"\n\2"), (r"\n(if \w+ >= 2:\n    \w+ = .*)\n(print)", r"\n\2")])
    elif n == "slices":
        sh = ("sum" if "sum(" in last else "concat") + ("_str" if ss else "_list")
        L["S.ignore_step"] = mrun(src, [(r":\(?-?\d+\)?\]", "]")])
    elif n == "string_pair_table":
        a, b = ss[0], ss[1]
        kind = "lcs" if "max(" in src else "edit"
        shp = "cell" if re.search(r"\]\)$", last) and ":]" not in last and "sum(" not in last else ("lastrow" if ":]" in last else "tablesum")
        sh = f"{kind}_{shp}"
        if shp == "cell":
            if kind == "edit":
                L["S.hamming_plus_lendiff"] = str(sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b)))
            else:
                L["S.common_multiset"] = str(sum((Counter(a) & Counter(b)).values()))
                L["S.min_len"] = str(min(len(a), len(b)))
    return sh, L


def generic_preds(src, tree):
    P = {}
    ints = ints_in_order(tree)
    for k in range(6):
        P[f"G.lit{k}"] = str(ints[k]) if k < len(ints) else None
        P[f"G.litr{k+1}"] = str(ints[-k - 1]) if k < len(ints) else None
    lists = int_lists(tree)
    ss = strs(tree)
    if lists:
        x = lists[0]
        P["G.L.len"], P["G.L.sum"], P["G.L.max"], P["G.L.min"], P["G.L.echo"] = str(len(x)), str(sum(x)), str(max(x)), str(min(x)), str(x)
        P["G.L.sorted"], P["G.L.rsorted"] = str(sorted(x)), str(sorted(x, reverse=True))
        P["G.L.first"], P["G.L.last"] = str(x[0]), str(x[-1])
    if ss:
        P["G.S.echo"], P["G.S.len"], P["G.S.rev"] = ss[0], str(len(ss[0])), ss[0][::-1]
    for c in ("0", "1", "-1", "2", "[]", ""):
        P[f"G.const{c}"] = c
    return P


def item_record(row):
    src = row["src"]
    tree = ast.parse(src)
    try:
        sh, S = specific(row["lid"], src, tree)
        err = None
    except Exception as ex:  # a rule-parsing failure is recorded, not hidden
        sh, S, err = "PARSE_FAIL", {}, f"{type(ex).__name__}: {ex}"
    G = generic_preds(src, tree)
    pf = ast.dump(print_arg(tree)) if False else None
    return {"lid": row["lid"], "lv": row["lv"], "i": row["i"], "key": row["key"], "shape": sh, "R": {**S, **G}, "err": err}


def process_file(args):
    fn, out_dir = args
    rows = [json.loads(l) for l in gzip.open(fn, "rt")]
    recs = [item_record(r) for r in rows]
    of = os.path.join(out_dir, os.path.basename(fn))
    with gzip.open(of, "wt") as f:
        for x in recs:
            f.write(json.dumps(x) + "\n")
    return rows[0]["lid"], sum(1 for x in recs if x["err"]), Counter(x["shape"] for x in recs)


def main():
    gen, out_dir = sys.argv[1], sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    files = sorted(glob.glob(os.path.join(gen, "*.jsonl.gz")))
    if len(sys.argv) > 3:
        files = [f for f in files if any(k + ".jsonl.gz" == os.path.basename(f) for k in sys.argv[3].split(","))]
    with ProcessPoolExecutor(12) as ex:
        for lid, nerr, shapes in ex.map(process_file, [(f, out_dir) for f in files]):
            print(lid, "parse_fail", nerr, dict(shapes), flush=True)


if __name__ == "__main__":
    main()
