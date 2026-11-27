# ruff: noqa
"""Final C1 audit (fix 4), step 5: closed-form search in sieve_marking_f4, fast_power_f4, counter_list_f3, func_branch_f4, func_compose_f4, slices_f4
(stdlib only; reads the program from the item TEXT; imports nothing from studies/). Rates are hits / items of the lineage and level (base rate 0, open answers).

sieve_marking_f4  F.order_free_strikesum: the indices i that run a strike pass are those with init[i] == 1 and NO initially flagged d < i with d | i and
                  i >= start(d) (the same order-free divisor test as the flags-shape closed form of audit 4 section 3); the answer is then the sum over those i
                  of the arithmetic series start(i), start(i) + i, ... < n (closed sum, no loop over j). No pass is simulated.
                  S.initial_flags_series: the same sum over every initially flagged i (ignores clearing; the audit's M.use_initial_flags is this as a mutation).
fast_power_f4     F.pow_res_c0: pow(b, e, m) (the unmodified algorithm); F.affine guesses (c ignored after first square, etc.)
counter_list_f3   F.residue_hist, F.prefix_hist (as audit 4), F.last_state_only: none expected.
func_branch_f4    the function applied to each literal argument IS the program; no closed form short of evaluating it. S.no_even_branch is reported (class M).
func_compose_f4   F.affine_collapse: f(f(x)) = a^2 x + ab + b computed directly (equal work: it is the program); reported for completeness.
slices_f4         S.ignore_negative_step: slices with negative steps read as positive (a convention error, not a shortcut); reported.
Usage: python3 f5_closed_forms.py GEN_DIR OUT_JSON
"""
import ast, gzip, json, os, re, sys
from collections import Counter, defaultdict

PRE = "Here is a Python program.\n\n"
SUF = "\n\nWhat exactly does it print? It prints a single line."


def lit(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, int) and not isinstance(n.value, bool):
        return n.value
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub) and isinstance(n.operand, ast.Constant):
        return -n.operand.value
    return None


def ap_sum(a, step, n):
    """sum of a, a+step, ... < n (closed)"""
    if a >= n:
        return 0
    k = (n - 1 - a) // step + 1
    return k * a + step * k * (k - 1) // 2


def sieve(src):
    t = ast.parse(src)
    fl = [lit(e) for e in t.body[0].value.elts]
    n = len(fl)
    m = re.search(r"^        (\w+) = (\w+) \+ \2$", src, re.M)
    mult = 2 if m else 3
    if not m:
        assert re.search(r"^        \w+ = 3 \* \w+$", src, re.M), src
    start = lambda i: mult * i
    alive = [i for i in range(2, n) if fl[i] == 1 and not any(fl[d] == 1 and i % d == 0 and i >= start(d) for d in range(2, i))]
    order_free = sum(ap_sum(start(i), i, n) for i in alive)
    init_all = sum(ap_sum(start(i), i, n) for i in range(2, n) if fl[i] == 1)
    # cheaper still: only primes flagged (ignores composites that were not struck)
    return {"F.order_free_strikesum": str(order_free), "S.initial_flags_series": str(init_all)}


def fast_power(src):
    t = ast.parse(src)
    vals = {}
    for s in t.body:
        if isinstance(s, ast.Assign) and lit(s.value) is not None:
            vals[s.targets[0].id] = lit(s.value)
    names = list(vals)
    res, b, e, m = names[:4]
    B0, E0, M0 = vals[b], vals[e], vals[m]
    c = int(re.search(r"\* \w+ \+ (\d+)\) %", src).group(1))
    out = {"F.pow_res_c0": str(pow(B0, E0, M0))}
    # res with c added only once per bit (affine guess): product of (B0^(2^k) + c) over set bits
    bb, r = B0, 1
    for k in range(E0.bit_length()):
        if (E0 >> k) & 1:
            r = r * ((pow(B0, 2 ** k, M0) + (c if k else 0)) % M0) % M0
    out["S.pow_terms_plus_c"] = str(r)
    out["S.last_b_power"] = str(pow(B0, 2 ** (E0.bit_length() - 1), M0))
    return out


def counter_list(src):
    t = ast.parse(src)
    vals = [lit(e) for e in t.body[0].value.elts]
    k = len(t.body[1].value.elts)
    c = [0] * k
    for v in vals:
        c[v % k] += 1
    out = {"F.residue_hist": str(c)}
    st, c2 = 0, [0] * k
    for v in vals:
        st = (st + v) % k
        c2[st] += 1
    out["F.prefix_hist"] = str(c2)
    mul = re.search(r"\(\w+ \* (\d+) \+ \w+\) % \d+", src)
    if mul:
        mu = int(mul.group(1))
        st, c3 = 0, [0] * k
        for v in vals:  # style 0 everywhere (ignores the data-dependent branch)
            st = (st * mu + v) % k
            c3[st] += 1
        out["M.style0_everywhere"] = str(c3)
    out["S.uniform"] = str([len(vals) // k + (1 if q < len(vals) % k else 0) for q in range(k)])
    return out


def run_mut(src):
    import contextlib, io, signal
    buf = io.StringIO()
    def _al(s, f):
        raise TimeoutError
    old = signal.signal(signal.SIGALRM, _al)
    try:
        signal.setitimer(signal.ITIMER_REAL, 2.0)
        with contextlib.redirect_stdout(buf):
            exec(compile(src, "<m>", "exec"), {})
        signal.setitimer(signal.ITIMER_REAL, 0)
    except BaseException:
        signal.setitimer(signal.ITIMER_REAL, 0)
        return None
    finally:
        signal.signal(signal.SIGALRM, old)
    v = buf.getvalue()
    return v[:-1] if v.endswith("\n") else None


def func_branch(src):
    out = {}
    s2 = re.sub(r"^    elif \w+ % 2 == 0:\n        return .*\n", "", src, flags=re.M)
    out["M.no_even_branch"] = run_mut(s2) if s2 != src else None
    # every call taking the threshold branch: a*x - b for all args (no comparison)
    m = re.search(r"if (\w+) > (\d+):\n        return \1 \* (\d+) - (\d+)", src)
    if m:
        a, b = int(m.group(3)), int(m.group(4))
        s3 = re.sub(r"if (\w+) > (\d+):", r"if True:", src, count=1)
        out["S.always_high_branch"] = run_mut(s3)
    return out


def slices(src):
    s2 = re.sub(r":\(-(\d)\)\]", r":\1]", src)
    return {"H.negative_step_as_positive": run_mut(s2) if s2 != src else None}


FNS = {"C1.sieve_marking_f4": sieve, "C1.fast_power_f4": fast_power, "C1.counter_list_f3": counter_list, "C1.func_branch_f4": func_branch, "C1.slices_f4": slices}


def main():
    gen, outp = sys.argv[1], sys.argv[2]
    res = {}
    for fid, fn in FNS.items():
        base = {"C1.sieve_marking_f4": "sieve_marking_f3", "C1.fast_power_f4": "fast_power_f3", "C1.func_branch_f4": "func_branch", "C1.slices_f4": "slices"}.get(fid, fid.replace("C1.", ""))
        rows = [json.loads(l) for l in gzip.open(os.path.join(gen, base + ".jsonl.gz"), "rt")]
        per = defaultdict(Counter)
        nlv = Counter()
        errs = Counter()
        for r in rows:
            src = r["q"][len(PRE):-len(SUF)]
            nlv[r["lv"]] += 1
            try:
                preds = fn(src)
            except Exception as ex:
                errs[type(ex).__name__] += 1
                continue
            for k, v in preds.items():
                if v is not None and v == r["key"]:
                    per[r["lv"]][k] += 1
        res[fid] = {"per_level": {lv: {k: round(v / nlv[lv], 4) for k, v in sorted(per[lv].items())} for lv in sorted(nlv)}, "n_per_level": dict(nlv), "errors": dict(errs)}
        print(fid, json.dumps(res[fid]["per_level"]), dict(errs))
    json.dump(res, open(outp, "w"), indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
