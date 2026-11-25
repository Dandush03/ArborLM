# ruff: noqa
"""Audit step 6: shortcut measurement on the items drawn by a04 (1,000 distinct per level for the existing 14,
2,000 for the new 25). Own code throughout; reads only the gzip records written by a04 (tree + key).

Rules measured per lineage x level:
 * the author's heuristics, re-implemented from c1_shortcut_check.py (read, not imported): constant, lit_*, echo,
   list1_*, str1_*, the lineage-specific guess, and the two 'oracle' coverages;
 * the auditor's own: O1 shape-constant (most frequent key per canonical print expression, 2-fold cross-validated),
   O2 last top-level int literal assigned, O3 first loop bound, O4 longest list literal length, O5 best single literal rule
   (chosen on one half from ~60 candidate rules, scored on the other half), O6 rate of key '0', O7 best rule per print
   shape (constant or any O5 candidate, chosen per shape on one half, scored on the other), and lineage-specific
   recognition rules R* (closed forms a reader can apply without tracing statement by statement).
Run: python a07_shortcuts.py gen1   (plain python is enough; imports only a02/a06 and the stdlib)
"""
import gzip
import json
import math
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from a02_myeval import canonical, to_str
from a06_feats import facts

_hz = Counter()
S = lambda v: to_str(v, _hz)


def mode(xs):
    c = Counter(xs)
    return min(c, key=lambda k: (-c[k], k))


def list_stats(xs):
    return {"first": S(xs[0]), "last": S(xs[-1]), "sum": S(sum(xs)), "len": S(len(xs)), "max": S(max(xs)), "min": S(min(xs)),
            "mode": S(mode(xs)), "posum": S(sum(x for x in xs if x > 0)), "sorted": S(sorted(xs)), "rev": S(xs[::-1]),
            "sorted_desc": S(sorted(xs, reverse=True))}


def author_rules():
    R = {
        "A.lit_first": lambda f, p: S(f["nums"][0]) if f["nums"] else None,
        "A.lit_last": lambda f, p: S(f["nums"][-1]) if f["nums"] else None,
        "A.lit_max": lambda f, p: S(max(f["nums"])) if f["nums"] else None,
        "A.lit_min": lambda f, p: S(min(f["nums"])) if f["nums"] else None,
        "A.lit_mode": lambda f, p: S(mode(f["nums"])) if f["nums"] else None,
        "A.echo_printed_initial": lambda f, p: f["echo"],
    }
    for st in ("first", "last", "sum", "len", "max", "min", "mode", "posum", "sorted", "rev", "sorted_desc"):
        R["A.list1_" + st] = (lambda st: lambda f, p: list_stats(f["flat"][0])[st] if f["flat"] else None)(st)
    for k in ("len", "rev", "self", "first", "last"):
        def g(f, p, k=k):
            if not f["strs"]:
                return None
            s = f["strs"][0]
            return {"len": S(len(s)), "rev": s[::-1], "self": s, "first": s[0] if s else None, "last": s[-1] if s else None}[k]
        R["A.str1_" + k] = g
    return R


AUTHOR_SPECIFIC = {
    "C1.binary_search": lambda f, p: S(len(f["flat"][0]).bit_length()) if f["flat"] else None,
    "C1.sieve_marking": lambda f, p: S(sum(f["flat"][0])) if f["flat"] else None,
    "C1.majority_vote_scan": lambda f, p: S(mode(f["flat"][0])) if f["flat"] else None,
    "C1.kadane_scan": lambda f, p: S(max(max(f["flat"][0]), sum(x for x in f["flat"][0] if x > 0))) if f["flat"] else None,
    "C1.insertion_sort": lambda f, p: S(sorted(f["flat"][0])) if f["flat"] else None,
    "C1.merge_two_sorted": lambda f, p: S(sorted(f["flat"][0] + f["flat"][1])) if len(f["flat"]) > 1 else None,
    "C1.circle_elimination": lambda f, p: S(len(f["flat"][0]) - 1) if f["flat"] else None,
    "C1.shared_lists": lambda f, p: S(f["flat"][0]) if f["flat"] else None,
    "C1.mirror_pointers": lambda f, p: S(len(f["strs"][0]) // 2) if f["strs"] else None,
    "C1.run_length_scan": lambda f, p: S(1 + sum(1 for a, b in zip(f["strs"][0], f["strs"][0][1:]) if a != b)) if f["strs"] else None,
}


def oracle_literal(f, ans):
    return ans in {S(x) for x in f["nums"]} or ans in f["strs"] or ans in {S(x) for x in f["lists"]}


def oracle_list_stat(f, ans):
    return any(ans in list_stats(xs).values() for xs in f["flat"]) or any(ans == S(len(s)) or ans in {S(s.count(c)) for c in sorted(set(s))} for s in f["strs"])


# ---------- auditor's candidate simple rules (for O5/O7)
def cand_rules():
    C = {}
    for k in range(10):
        C[f"num[{k}]"] = (lambda k: lambda f, p: S(f["nums"][k]) if len(f["nums"]) > k else None)(k)
        C[f"num[-{k+1}]"] = (lambda k: lambda f, p: S(f["nums"][-k - 1]) if len(f["nums"]) > k else None)(k)
    def kth(f, k, rev):
        xs = sorted(set(f["nums"]), reverse=rev)
        return S(xs[k]) if len(xs) > k else None
    for k in range(3):
        C[f"max#{k+1}"] = (lambda k: lambda f, p: kth(f, k, True))(k)
        C[f"min#{k+1}"] = (lambda k: lambda f, p: kth(f, k, False))(k)
    C["sum_nums"] = lambda f, p: S(sum(f["nums"])) if f["nums"] else None
    C["count_nums"] = lambda f, p: S(len(f["nums"]))
    C["n_distinct_nums"] = lambda f, p: S(len(set(f["nums"])))
    C["len_str1"] = lambda f, p: S(len(f["strs"][0])) if f["strs"] else None
    C["len_str_last"] = lambda f, p: S(len(f["strs"][-1])) if f["strs"] else None
    C["str1"] = lambda f, p: f["strs"][0] if f["strs"] else None
    C["len_list1"] = lambda f, p: S(len(f["flat"][0])) if f["flat"] else None
    C["len_list_last"] = lambda f, p: S(len(f["flat"][-1])) if f["flat"] else None
    C["len_list_longest"] = lambda f, p: S(max(len(x) for x in f["lists"])) if f["lists"] else None
    C["len_list1_minus1"] = lambda f, p: S(len(f["flat"][0]) - 1) if f["flat"] else None
    C["sum_list1"] = lambda f, p: S(sum(f["flat"][0])) if f["flat"] else None
    C["max_list1"] = lambda f, p: S(max(f["flat"][0])) if f["flat"] else None
    C["min_list1"] = lambda f, p: S(min(f["flat"][0])) if f["flat"] else None
    C["list1"] = lambda f, p: S(f["flat"][0]) if f["flat"] else None
    C["list1_sorted"] = lambda f, p: S(sorted(f["flat"][0])) if f["flat"] else None
    C["list1_sorted_desc"] = lambda f, p: S(sorted(f["flat"][0], reverse=True)) if f["flat"] else None
    C["ones_list1"] = lambda f, p: S(f["flat"][0].count(1)) if f["flat"] else None
    C["zeros_list1"] = lambda f, p: S(f["flat"][0].count(0)) if f["flat"] else None
    C["last_set_int"] = lambda f, p: last_set_int(p)
    C["loop_bound"] = lambda f, p: loop_bound(p)
    C["echo"] = lambda f, p: f["echo"]
    for c in ("0", "1", "2", "3"):
        C["const_" + c] = (lambda c: lambda f, p: c)(c)
    return C


def last_set_int(p):
    v = None
    for s in p:
        if s[0] == "set" and s[2][0] == "n":
            v = s[2][1]
    return S(v) if v is not None else None


def loop_bound(p):
    def walk(body):
        for s in body:
            if s[0] == "for" and s[3][0] == "n":
                return s[3][1]
            if s[0] == "while" and s[1][0] == "c" and s[1][3][0] == "n":
                return s[1][3][1]
            for sub in ([s[5]] if s[0] == "for" else [s[2]] if s[0] == "while" else [s[2], s[3]] if s[0] == "if" else [s[3]] if s[0] == "def" else []):
                r = walk(sub)
                if r is not None:
                    return r
        return None
    v = walk(p)
    return S(v) if v is not None else None


# ---------- lineage-specific recognition rules (auditor's; closed forms or naive readings)
def top_sets(p):
    return [(s[1], s[2]) for s in p if s[0] == "set"]


def R_euclid(f, p):
    x, y = f["nums"][0], f["nums"][1]
    return {"R.gcd_of_literals": S(math.gcd(x, y)), "R.min_literal": S(min(x, y)), "R.sum_quot_naive_max_div_min": S(max(x, y) // min(x, y))}


def R_fastpow(f, p):
    sets = [e for _, e in top_sets(p)]
    base, ex, mod = sets[1][1], sets[2][1], sets[3][1]
    bb = base
    for _ in range(ex.bit_length()):
        bb = bb * bb % mod
    return {"R.pow(base,exp,mod)": S(pow(base, ex, mod)), "R.base_mod": S(base % mod), "R.base^(2^bits)": S(bb)}


def R_digit(f, p):
    n = f["nums"][0]
    return {"R.decimal_digit_sum_of_literal": S(sum(int(c) for c in str(n))), "R.decimal_digit_count": S(len(str(n)))}


def R_insertion(f, p):
    xs = f["flat"][0]
    loop = [s for s in p if s[0] == "for"][0]
    k = loop[3][1]
    wh = loop[5][2]
    op = wh[1][2][1]
    desc = op in ("<", "<=")
    pre = sorted(xs[:k], reverse=desc)
    after = pre + xs[k:]
    pr = f["print"]
    out = {"R.sorted_prefix_list": S(after)}
    if pr[0] == "idx":
        out["R.sorted_prefix_at"] = S(after[pr[2][1]])
    strict = op in (">", "<")
    inv = 0
    for i in range(k):
        for j in range(i):
            a, b = xs[j], xs[i]
            if (a > b if op == ">" else a >= b if op == ">=" else a < b if op == "<" else a <= b):
                inv += 1
    out["R.inversions_prefix"] = S(inv)
    return out


def R_partition(f, p):
    xs = f["flat"][0]
    m = p[1][2][2][1] + 1  # pv = xs[m-1]
    piv = xs[m - 1]
    loop = [s for s in p if s[0] == "for"][0]
    op = loop[5][0][1][1]
    le = [x for x in xs[: m - 1] if (x <= piv if op == "<=" else x < piv)]
    gt = [x for x in xs[: m - 1] if not (x <= piv if op == "<=" else x < piv)]
    return {"R.stable_partition": S(le + [piv] + gt + xs[m:]), "R.input_list": S(xs)}


def max_sub(xs):
    best = cur = xs[0]
    for x in xs[1:]:
        cur = max(cur + x, x)
        best = max(best, cur)
    return best


def R_kadane(f, p):
    xs = f["flat"][0]
    return {"R.max_subarray": S(max_sub(xs)), "R.last_element": S(xs[-1])}


def R_majority(f, p):
    xs = f["flat"][0]
    return {"R.last_element": S(xs[-1]), "R.first_element": S(xs[0]), "R.mode_space_0": S(mode(xs)) + " 0"}


def R_bracket(f, p):
    s = f["strs"][0]
    opens = s.count("(") + s.count("[")
    net = opens - (len(s) - opens)
    st, err, first = [], 0, -1
    for i, ch in enumerate(s):
        if ch in "([":
            st.append(ch)
        elif st and ((ch == ")" and st[-1] == "(") or (ch == "]" and st[-1] == "[")):
            st.pop()
        else:
            err += 1
            first = i if first < 0 else first
    return {"R.net_balance": S(net), "R.opens": S(opens), "R.standard_height": S(len(st)), "R.standard_code": S(10 * err + len(st)), "R.standard_first": S(first)}


def R_coin(f, p):
    coins = f["flat"][0]
    T = None
    pr = f["print"]
    if pr[0] == "idx":
        T = pr[2][1]
    if T is None:
        return {}
    g, rem = 0, T
    for c in sorted(coins, reverse=True):
        g += rem // c
        rem %= c
    return {"R.greedy_fewest": S(g) if rem == 0 else None, "R.T_div_maxcoin": S(T // max(coins))}


def R_strpair(f, p):
    a, b = f["strs"][0], f["strs"][1]
    ham = sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b))
    ca, cb = Counter(a), Counter(b)
    overlap = sum(min(ca[c], cb[c]) for c in ca)
    return {"R.hamming_plus_lendiff": S(ham), "R.multiset_overlap": S(overlap), "R.len_a": S(len(a))}


def R_grid(f, p):
    g = f["lists"][0]
    r, c = len(g), len(g[0])
    out = {"R.binom_paths": S(math.comb(r + c - 2, r - 1))}
    i = j = 0
    tot_max = tot_min = g[0][0]
    i2 = j2 = 0
    while (i, j) != (r - 1, c - 1):
        if i == r - 1 or (j < c - 1 and g[i][j + 1] >= g[i + 1][j]):
            j += 1
        else:
            i += 1
        tot_max += g[i][j]
    while (i2, j2) != (r - 1, c - 1):
        if i2 == r - 1 or (j2 < c - 1 and g[i2][j2 + 1] <= g[i2 + 1][j2]):
            j2 += 1
        else:
            i2 += 1
        tot_min += g[i2][j2]
    out["R.greedy_max_path"] = S(tot_max)
    out["R.greedy_min_path"] = S(tot_min)
    return out


def R_union(f, p):
    n = len(f["flat"][0])
    us, vs = f["flat"][1], f["flat"][2]
    par = list(range(n))
    for u, v in zip(us, vs):
        par[u] = v
    par2 = list(range(n))
    for u, v in zip(us, vs):
        par2[v] = u
    return {"R.naive_links_u->v": S(par), "R.naive_links_v->u": S(par2), "R.identity": S(list(range(n)))}


def R_turtle(f, p):
    s = f["strs"][0]
    return {"R.F_minus_B": S(s.count("F") - s.count("B")), "R.count_F": S(s.count("F"))}


def R_bytecode(f, p):
    code = f["flat"][0]
    return {"R.sum_all_args": S(sum(code[1::2]))}


def R_sieve(f, p):
    fl = f["flat"][0]
    n = len(fl)
    pr = [i for i in range(2, n) if all(i % d for d in range(2, int(i ** 0.5) + 1))]
    return {"R.prime_count_below_n": S(len(pr)), "R.ones_minus_strikes_naive": S(sum(fl[:2]) + len([i for i in pr if fl[i]]))}


def R_mirror(f, p):
    s = f["strs"][0]
    n = len(s)
    return {"R.unequal_pairs": S(sum(1 for k in range(n // 2) if s[k] != s[n - 1 - k]))}


def R_merge(f, p):
    a, b = f["flat"][0], f["flat"][1]
    return {"R.len_a+len_b-1": S(len(a) + len(b) - 1), "R.sorted_all_but_last": S(sorted(a + b)[:-1])}


def R_circle(f, p):
    fl = f["flat"][0]
    return {"R.last_live_index": S(max(i for i, v in enumerate(fl) if v)), "R.first_live_index": S(min(i for i, v in enumerate(fl) if v))}


def R_postfix(f, p):
    toks = f["flat"][0]
    return {"R.last_operand": S([t for t in toks if t >= 0][-1]), "R.first_operand": S(toks[0])}


def R_string_build(f, p):
    loop = [s for s in p if s[0] == "for"][0]
    lo = loop[2][1]
    hi = loop[3][1]
    return {"R.iterations(stop-start)": S(hi - lo)}


def R_list_build(f, p):
    loop = [s for s in p if s[0] == "for"][0]
    app = loop[5][0][2]
    m = app[3][1]
    return {"R.m_minus_1": S(m - 1), "R.n_iterations": S(loop[3][1])}


def R_cond(f, p):
    sets = top_sets(p)
    a, b = sets[0][1][1], sets[1][1][1]
    return {"R.gcd_of_literals": S(math.gcd(a, b))}


SPECIFIC = {"C1.euclid_gcd": R_euclid, "C1.fast_power": R_fastpow, "C1.digit_peel": R_digit, "C1.insertion_sort": R_insertion,
            "C1.partition_pass": R_partition, "C1.kadane_scan": R_kadane, "C1.majority_vote_scan": R_majority, "C1.bracket_matching": R_bracket,
            "C1.coin_change_table": R_coin, "C1.string_pair_table": R_strpair, "C1.grid_path_table": R_grid, "C1.union_find_links": R_union,
            "C1.turtle_walk": R_turtle, "C1.bytecode_loop": R_bytecode, "C1.sieve_marking": R_sieve, "C1.mirror_pointers": R_mirror,
            "C1.merge_two_sorted": R_merge, "C1.circle_elimination": R_circle, "C1.postfix_evaluation": R_postfix,
            "C1.string_build": R_string_build, "C1.list_build": R_list_build, "C1.cond_chain": R_cond}


def shape_key(p, f):
    return json.dumps(canonical([["print", f["print"]]]))


def cv_constant_by_shape(items):
    """2-fold: fit most frequent key per shape on one half, score on the other."""
    hit = 0
    for fit, test in ((0, 1), (1, 0)):
        best = {}
        tab = defaultdict(Counter)
        for i, (sh, ans, _) in enumerate(items):
            if i % 2 == fit:
                tab[sh][ans] += 1
        for sh, c in tab.items():
            best[sh] = min(c, key=lambda k: (-c[k], k))
        for i, (sh, ans, _) in enumerate(items):
            if i % 2 == test and best.get(sh) == ans:
                hit += 1
    return hit / len(items)


def cv_best_rule(items, cands, per_shape):
    hit = 0
    names = sorted(cands)
    chosen_log = Counter()
    for fit, test in ((0, 1), (1, 0)):
        score = defaultdict(Counter)
        consts = defaultdict(Counter)
        for i, (sh, ans, g) in enumerate(items):
            if i % 2 != fit:
                continue
            key = sh if per_shape else "*"
            for nm in names:
                if g[nm] == ans:
                    score[key][nm] += 1
            consts[key][ans] += 1
        pick = {}
        for key in set(score) | set(consts):
            bn = max(names, key=lambda nm: (score[key][nm], nm)) if score[key] else None
            bc = min(consts[key], key=lambda a: (-consts[key][a], a)) if consts[key] else None
            if per_shape and bc is not None and consts[key][bc] > (score[key][bn] if bn else 0):
                pick[key] = ("const", bc)
            else:
                pick[key] = ("rule", bn)
            chosen_log[pick[key][1] if pick[key][0] == "rule" else "const"] += 1
        for i, (sh, ans, g) in enumerate(items):
            if i % 2 != test:
                continue
            key = sh if per_shape else "*"
            pk = pick.get(key)
            if pk is None:
                continue
            if (pk[0] == "const" and pk[1] == ans) or (pk[0] == "rule" and pk[1] is not None and g[pk[1]] == ans):
                hit += 1
    return hit / len(items), chosen_log.most_common(3)


def analyse(sub):
    d = os.path.join(HERE, sub)
    summ = json.load(open(os.path.join(d, "summary.json")))
    AR = author_rules()
    CR = cand_rules()
    res = {}
    for lid in summ["old"] + summ["new"]:
        res[lid] = {}
        for lv in range(7):
            recs = [json.loads(l) for l in gzip.open(os.path.join(d, f"items_{lid}_L{lv}.jsonl.gz"), "rt")]
            n = len(recs)
            row = {"n": n}
            ans = [r["ans"] for r in recs]
            cnt = Counter(ans)
            top, topn = min(cnt.items(), key=lambda kv: (-kv[1], kv[0]))
            row["distinct_keys"] = len(cnt)
            row["const_overall"] = topn / n
            row["const_key"] = top[:30]
            fs = [facts(r["prog"]) for r in recs]
            # author battery
            for nm, g in AR.items():
                row[nm] = sum(1 for f, r in zip(fs, recs) if g(f, r["prog"]) == r["ans"]) / n
            if lid in AUTHOR_SPECIFIC:
                g = AUTHOR_SPECIFIC[lid]
                row["A.specific"] = sum(1 for f, r in zip(fs, recs) if g(f, r["prog"]) == r["ans"]) / n
            row["A.oracle_any_literal"] = sum(oracle_literal(f, r["ans"]) for f, r in zip(fs, recs)) / n
            row["A.oracle_list_or_string_stat"] = sum(oracle_list_stat(f, r["ans"]) for f, r in zip(fs, recs)) / n
            # own
            shapes = [shape_key(r["prog"], f) for f, r in zip(fs, recs)]
            guesses = [{nm: c(f, r["prog"]) for nm, c in CR.items()} for f, r in zip(fs, recs)]
            items = list(zip(shapes, ans, guesses))
            row["O1.shape_const_cv"] = cv_constant_by_shape(items)
            row["O2.last_set_int"] = sum(1 for g, a in zip(guesses, ans) if g["last_set_int"] == a) / n
            row["O3.loop_bound"] = sum(1 for g, a in zip(guesses, ans) if g["loop_bound"] == a) / n
            row["O4.len_list_longest"] = sum(1 for g, a in zip(guesses, ans) if g["len_list_longest"] == a) / n
            row["O5.best_literal_rule_cv"], row["O5.chosen"] = cv_best_rule(items, CR, False)
            row["O6.key_is_0"] = cnt.get("0", 0) / n
            row["O7.best_rule_per_shape_cv"], row["O7.chosen"] = cv_best_rule(items, CR, True)
            row["n_shapes"] = len(set(shapes))
            # specific recognition rules
            if lid in SPECIFIC:
                tab = Counter()
                app = Counter()
                for f, r in zip(fs, recs):
                    try:
                        gs = SPECIFIC[lid](f, r["prog"])
                    except Exception as ex:
                        tab["_error:" + type(ex).__name__] += 1
                        continue
                    for k, v in gs.items():
                        if v is not None:
                            app[k] += 1
                        if v == r["ans"]:
                            tab[k] += 1
                for k in sorted(set(tab) | set(app)):
                    row[k] = tab[k] / n
            res[lid][lv] = row
    return summ, res


if __name__ == "__main__":
    sub = sys.argv[1]
    summ, res = analyse(sub)
    out = os.path.join(HERE, f"a07_shortcuts_{sub}.json")
    json.dump(res, open(out, "w"), indent=1, sort_keys=True)
    print("wrote", out)
