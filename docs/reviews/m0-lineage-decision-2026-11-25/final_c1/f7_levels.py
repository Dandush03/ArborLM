# ruff: noqa
"""Final C1 audit (fix 4), step 7: are the levels distinct, and does difficulty rise with the level? (stdlib only; program read from the item TEXT.)

My criterion (independent of the implementer's 'shared-stream 99 % identical' test, which needs the generator's stream):
  (a) distinct: within each level the share of distinct normalised texts, and the share of a level's items whose normalised text occurs at ANY other level
      (cross-level repeats); a level pair is NOT distinct if its item distributions cannot be told apart: two-sample tests on every feature below all give
      |z| < 3.29 (two-sided p > 0.001) AND the cross-level repeat share is above 1 %.
  (b) rising: for each step L -> L+1, one-sided Mann-Whitney z (normal approximation, ties averaged) of each feature, L+1 above L; the step RISES if at least
      one feature has z >= 3.09 (p < 0.001) and no feature falls with z <= -3.09 unless another rises; the feature tied to the docstring's stated parameter is
      named in the output (PARAM) and checked by itself.
Features per item: executed line events (sys.settrace in-process, my own exec with a 5 s alarm), characters of the program, AST nodes, largest |int literal|,
longest list/string literal, number of call sites, number of top-level statements.
Usage: python3 f7_levels.py GEN_DIR OUT_JSON
"""
import ast, contextlib, gzip, glob, io, json, math, os, re, signal, sys, unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

PRE = "Here is a Python program.\n\n"
SUF = "\n\nWhat exactly does it print? It prints a single line."

# the docstring's stated difficulty parameter, mapped to the feature that measures it (my reading of each builder's docstring)
PARAM = {
    "C1.binary_search_f3": "longest_literal", "C1.bracket_matching_f3": "longest_literal", "C1.bytecode_loop_f3": "steps",
    "C1.circle_elimination_r2": "longest_literal", "C1.cond_chain_f3": "steps", "C1.counter_list_f3": "longest_literal",
    "C1.digit_peel_f3": "max_literal", "C1.euclid_gcd_traced_f3": "max_literal", "C1.fast_power_f4": "max_literal",
    "C1.fib_like_f3": "steps", "C1.fib_shapes_recursive_f3": "steps", "C1.func_branch_f4": "max_literal",
    "C1.func_compose_f4": "max_literal", "C1.list_build_f3": "steps", "C1.merge_two_sorted_f3": "longest_literal",
    "C1.nested_pairs_f3": "steps", "C1.postfix_evaluation": "longest_literal", "C1.recursive_calls_r2": "steps",
    "C1.run_length_scan": "longest_literal", "C1.shared_lists_f3": "top_statements", "C1.sieve_marking_f4": "longest_literal",
    "C1.slices_f4": "longest_literal", "C1.string_build_f3": "steps", "C1.string_methods_f3": "chars",
    "C1.turtle_walk_f3": "longest_literal", "C1.union_find_links_f3": "longest_literal", "C1.while_counter_f3": "max_literal",
}
FEATS = ("steps", "chars", "ast_nodes", "max_literal", "longest_literal", "calls", "top_statements")


def norm(t):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", t).casefold()).strip()


def steps(src):
    n = [0]
    def tr(frame, ev, arg):
        if ev == "line" and frame.f_code.co_filename == "<p>":
            n[0] += 1
        return tr
    def _al(s, f):
        raise TimeoutError
    old = signal.signal(signal.SIGALRM, _al)
    buf = io.StringIO()
    try:
        signal.setitimer(signal.ITIMER_REAL, 5.0)
        sys.settrace(tr)
        with contextlib.redirect_stdout(buf):
            exec(compile(src, "<p>", "exec"), {"__name__": "__p__"})
    except BaseException:
        n[0] = -1
    finally:
        sys.settrace(None)
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)
    return n[0]


def feats(src):
    t = ast.parse(src)
    ints = [abs(n.value) for n in ast.walk(t) if isinstance(n, ast.Constant) and isinstance(n.value, int) and not isinstance(n.value, bool)]
    lens = [len(n.elts) for n in ast.walk(t) if isinstance(n, ast.List)] + [len(n.value) for n in ast.walk(t) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    return {"steps": steps(src), "chars": len(src), "ast_nodes": sum(1 for _ in ast.walk(t)), "max_literal": max(ints, default=0),
            "longest_literal": max(lens, default=0), "calls": sum(1 for n in ast.walk(t) if isinstance(n, ast.Call)), "top_statements": len(t.body)}


def mwu_z(x, y):
    """z of Mann-Whitney U for y > x (normal approximation, tie-corrected)."""
    allv = sorted([(v, 0) for v in x] + [(v, 1) for v in y])
    ranks = [0.0] * len(allv)
    i = 0
    tie = 0.0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1][0] == allv[i][0]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = r
        c = j - i + 1
        tie += c ** 3 - c
        i = j + 1
    n1, n2 = len(x), len(y)
    R2 = sum(r for r, (v, g) in zip(ranks, allv) if g == 1)
    U = R2 - n2 * (n2 + 1) / 2
    N = n1 + n2
    var = n1 * n2 / 12 * ((N + 1) - tie / (N * (N - 1)))
    return 0.0 if var <= 0 else (U - n1 * n2 / 2) / math.sqrt(var)


def one(fn):
    rows = [json.loads(l) for l in gzip.open(fn, "rt")]
    fid = rows[0]["fid"]
    by = defaultdict(list)
    texts = defaultdict(list)
    for r in rows:
        src = r["q"][len(PRE):-len(SUF)]
        by[r["lv"]].append(feats(src))
        texts[r["lv"]].append(norm(r["q"]))
    out = {"fid": fid, "param_feature": PARAM.get(fid), "levels": {}, "steps": {}}
    where = defaultdict(set)
    for lv, ts in texts.items():
        for t in ts:
            where[t].add(lv)
    for lv in range(7):
        ts = texts[lv]
        out["levels"][lv] = {"n": len(ts), "distinct_share": round(len(set(ts)) / len(ts), 4),
                             "cross_level_repeat_share": round(sum(1 for t in ts if len(where[t]) > 1) / len(ts), 4),
                             "mean": {f: round(sum(x[f] for x in by[lv]) / len(by[lv]), 2) for f in FEATS},
                             "steps_failed": sum(1 for x in by[lv] if x["steps"] < 0)}
    for lv in range(6):
        z = {f: round(mwu_z([x[f] for x in by[lv]], [x[f] for x in by[lv + 1]]), 2) for f in FEATS}
        rise = [f for f, v in z.items() if v >= 3.09]
        fall = [f for f, v in z.items() if v <= -3.09]
        rep = max(out["levels"][lv]["cross_level_repeat_share"], out["levels"][lv + 1]["cross_level_repeat_share"])
        indist = all(abs(v) < 3.29 for v in z.values()) and rep > 0.01
        pf = PARAM.get(fid)
        out["steps"][f"L{lv}->L{lv+1}"] = {"z": z, "rises_in": rise, "falls_in": fall, "RISES": bool(rise), "NOT_DISTINCT": indist,
                                           "param_feature_z": z.get(pf), "param_feature_rises": (z.get(pf) or 0) >= 3.09}
    return out


def main():
    gen, outp = sys.argv[1], sys.argv[2]
    files = sorted(glob.glob(os.path.join(gen, "*.jsonl.gz")))
    res = {}
    with ProcessPoolExecutor(6) as ex:
        for o in ex.map(one, files):
            res[o["fid"]] = o
            bad = [k for k, v in o["steps"].items() if not v["RISES"] or v["NOT_DISTINCT"] or v["falls_in"]]
            pbad = [k for k, v in o["steps"].items() if not v["param_feature_rises"]]
            print(f"{o['fid']:30s} max_cross_repeat={max(v['cross_level_repeat_share'] for v in o['levels'].values()):.4f} "
                  f"min_distinct={min(v['distinct_share'] for v in o['levels'].values()):.4f} steps_not_rising_or_falling={bad} param({o['param_feature']})_not_rising={pbad}", flush=True)
    json.dump(res, open(outp, "w"), indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
