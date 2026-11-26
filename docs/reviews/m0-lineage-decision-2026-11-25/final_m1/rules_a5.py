# ruff: noqa
"""Final M1 audit (fix 4): cheap-rule measurement on the 29 survivors.
Rule DEFINITIONS are read unchanged from the audit scripts (audit3_m1/shortcuts_a3.spec, audit4_m1/shortcuts_a4.mine and visible_class) and from the
implementer's battery (studies.m0.m1_fix3_shortcuts.spec), loaded with importlib; the SCORING is re-implemented here to the same definitions as those scripts
(base = most frequent answer fitted on one half and scored on the other, two folds by index parity; rates over ALL items, a rule that does not apply is a miss;
echo-by-best-position fitted on one half; a4 mode-by-visible-ask held out with the global mode as fallback). The implementer's summary script
(m1_fix4_battery / m1_fix4_survivors) is NOT used.
NEW rules (auditor's, reported separately, class NEW):
  new:one_op_two_numbers   x op y over printed numbers at positions (first 6 and last 3), op in + - * /, best (i, j, op) fitted on one half, scored on the other
  new:mode_by_template     most frequent answer per masked text template (digits and capitalised names masked; setting sentence removed), held out
  new:median_midrange      (min + max) / 2 (median_list)
  new:avg_ignore_count     mean + (mean - mean of the shown scores) (average_missing)
  new:clock_hhmm_subtract  sum over legs of (HHMM arrival - HHMM departure) read as plain numbers (clock_duration)
  new:fd_deg2_last3        constant second difference from the last three terms, for degree-3 items (finite_differences)
  new:ratio_first_named / new:ratio_last_named   share of the first / last named person (ratio_share; a person guess like largest_share)
Attempt 2: attempt 1 (rules_a5_attempt1.py) broke ties of the a3/own echo rule in the a4 candidate order; one of 3,190 recomputed values differed
(mixture L3 a3 echo 0.000 vs 0.002). The a3/own echo now uses the a3 candidate order. My error (tie handling).
Modes:
  fresh N SEED out.json : items from core.stream(SEED, 'final-m1-a5', 'rules', id, level); all rule sets scored on the same items
  repro N out.json      : items from the implementer's / auditors' own streams (a4: seed 17 'audit4-m1' 'short'; own: 410302 'fix3-shortcuts'; a3: seed 5 'audit3-m1' 'short'),
                          each source's rules scored on its own stream, to recompute the implementer's raw figures independently."""
import importlib.util
import json
import math
import re
import sys
from collections import Counter, defaultdict
from fractions import Fraction as F
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fm1_common import items, stem, survivors
from studies.m0.core import build_item, stream

AUD = Path("docs/reviews/m0-lineage-decision-2026-11-25").resolve()


def _load(path, name):
    sys.path.insert(0, str(Path(path).parent))
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def mods():
    a4 = _load(AUD / "audit4_m1" / "shortcuts_a4.py", "shortcuts_a4_final")
    a3 = _load(AUD / "audit3_m1" / "shortcuts_a3.py", "shortcuts_a3_final")
    import studies.m0.m1_fix3_shortcuts as im
    return a3, a4, im


def nums_a3(q):
    return [F(x) for x in re.findall(r"(?<![\w.])\d+(?:\.\d+)?", q.replace("$", " "))]


CANDS = {"first": lambda L: L[0], "second": lambda L: L[1] if len(L) > 1 else None, "last": lambda L: L[-1], "second_last": lambda L: L[-2] if len(L) > 1 else None,
         "max": max, "min": min, "sum": lambda L: sum(L), "max_minus_min": lambda L: max(L) - min(L)}
CTX = [r"^\S+ from \S+ found this problem in a puzzle book\. ", r"^This problem comes from a quiz held in [^,]+, set by \S+\. ", r"^\S+ of \S+ wrote this problem for a maths club\. ", r"^At a maths club in [^,]+, \S+ is asked this\. "]


def template(q):
    for c in CTX:
        q = re.sub(c, "", q)
    q = re.sub(r"\d+(\.\d+)?", "#", q)
    return re.sub(r"\b[A-Z][a-z]+\b", "W", q)


def heldout_mode(classes, ans):
    N = len(ans)
    ev, od = list(range(0, N, 2)), list(range(1, N, 2))
    r = 0
    for tr, te in ((ev, od), (od, ev)):
        by = defaultdict(Counter)
        allc = Counter()
        for i in tr:
            by[classes[i]][ans[i]] += 1
            allc[ans[i]] += 1
        g = allc.most_common(1)[0][0]
        r += sum(1 for i in te if (by[classes[i]].most_common(1)[0][0] if by[classes[i]] else g) == ans[i]) / len(te)
    return r / 2


A3_ORDER = ("first", "second", "last", "max", "min", "sum", "max_minus_min", "second_last")  # candidate order of shortcuts_a3 / m1_fix3_shortcuts (ties -> first in this order)
A4_ORDER = ("first", "second", "last", "second_last", "max", "min", "sum", "max_minus_min")  # candidate order of shortcuts_a4


def echo_best(numl, ans, offsets=(0,), order=A4_ORDER):
    N = len(ans)
    ev, od = list(range(0, N, 2)), list(range(1, N, 2))

    def r_pos(fn, off, idx):
        return sum(1 for i in idx if numl[i] and fn(numl[i]) is not None and fn(numl[i]) + off == ans[i]) / len(idx)
    e = 0
    for tr, te in ((ev, od), (od, ev)):
        k, o = max(((k, o) for k in order for o in offsets), key=lambda ko: r_pos(CANDS[ko[0]], ko[1], tr))
        e += r_pos(CANDS[k], o, te) / 2
    return e


def one_op(numl, ans):
    """new:one_op_two_numbers, held out (fit on one half, score on the other)."""
    N = len(ans)
    pos = [0, 1, 2, 3, 4, 5, -1, -2, -3]
    ops = ("+", "-", "*", "/")
    hits = []  # per item: set of (i, j, op) that give the answer
    for L, a in zip(numl, ans):
        s = set()
        n = len(L)
        for i in pos:
            if not (-n <= i < n):
                continue
            x = L[i]
            for j in pos:
                if j == i or not (-n <= j < n) or (j % n) == (i % n):
                    continue
                y = L[j]
                if x + y == a: s.add((i, j, "+"))
                if x - y == a: s.add((i, j, "-"))
                if x * y == a: s.add((i, j, "*"))
                if y != 0 and x / y == a: s.add((i, j, "/"))
        hits.append(s)
    ev, od = list(range(0, N, 2)), list(range(1, N, 2))
    r = 0
    best = []
    for tr, te in ((ev, od), (od, ev)):
        c = Counter()
        for i in tr:
            c.update(hits[i])
        if not c:
            best.append(None)
            continue
        k = c.most_common(1)[0][0]
        best.append(k)
        r += sum(1 for i in te if k in hits[i]) / len(te) / 2
    return r, best


def new_specific(st, s, q):
    h = {}
    if st == "median_list":
        v = s["values"]
        h["new:median_midrange"] = F(min(v) + max(v), 2)
    elif st == "average_missing":
        sc, n, mean = s["scores"], s["n"], F(s["mean_cents"], 100)
        h["new:avg_ignore_count"] = mean + (mean - F(sum(sc), len(sc)))
    elif st == "clock_duration":
        h["new:clock_hhmm_subtract"] = F(sum((b // 60 * 100 + b % 60) - (a // 60 * 100 + a % 60) for a, b in s["legs"]))
    elif st == "finite_differences":
        t = s["terms"]
        if s["degree"] == 3:
            d1 = [b - a for a, b in zip(t, t[1:])]
            d2 = d1[-1] - d1[-2]
            last, d = t[-1], d1[-1]
            for _ in range(s["ask"] - len(t)):
                d += d2
                last += d
            h["new:fd_deg2_last3"] = F(last)
    elif st == "ratio_share":
        p, tot = s["parts"], s["total"]
        h["new:ratio_first_named"] = F(tot * p[0], sum(p))
        h["new:ratio_last_named"] = F(tot * p[-1], sum(p))
    return h


def score(st, its, which, a3, a4, im, with_new):
    """Return {rule: rate} plus base, for the rule sets in `which` (subset of a3, a4, im)."""
    ans = [F(it.answer) for it in its]
    N = len(ans)
    base = heldout_mode([0] * N, ans)
    numl = [nums_a3(it.question) for it in its]
    rates = {}
    skipped = 0
    if "a3" in which or "im" in which:
        rates["echo_best_position"] = echo_best(numl, ans, order=A3_ORDER)
    if "a4" in which:
        rates["a4:echo_pos"] = echo_best(numl, ans)
        rates["a4:echo_pos_offset"] = echo_best(numl, ans, range(-12, 13))
        rates["a4:mode_by_visible_ask"] = heldout_mode([a4.visible_class(st, it.structured) for it in its], ans)
    sp = []
    for it in its:
        d = {}
        if "a4" in which:
            d.update(a4.mine(st, it.structured, it.question))
        if "im" in which:
            d.update({f"im:{k}": v for k, v in im.spec(st, it.structured).items()})
        if "a3" in which:
            try:
                d.update({f"a3:{k}": v for k, v in a3.spec("power_remainder" if st == "last_digit_power" else st, it.structured, it.question).items()})
            except Exception:
                skipped += 1
        if with_new:
            d.update(new_specific(st, it.structured, it.question))
        sp.append(d)
    names = sorted({k for d in sp for k in d})
    within = {}
    for k in names:
        app = [(d[k], a) for d, a in zip(sp, ans) if d.get(k) is not None]
        rates[k] = sum(1 for v, a in app if v == a) / N
        if len(app) < N:
            within[k] = [sum(1 for v, a in app if v == a) / max(1, len(app)), len(app)]
    extra = {}
    if with_new:
        r, best = one_op(numl, ans)
        rates["new:one_op_two_numbers"] = r
        extra["one_op_best"] = [str(b) for b in best]
        rates["new:mode_by_template"] = heldout_mode([template(it.question) for it in its], ans)
        if st == "ratio_share":
            # diagnostic: is the asked person the largest-part holder more often than 1/k?
            exp = sum(F(sum(1 for x in it.structured["parts"] if x == max(it.structured["parts"])), len(it.structured["parts"])) for it in its) / N
            obs = sum(1 for it in its if it.structured["parts"][it.structured["who"]] == max(it.structured["parts"])) / N
            extra["asked_is_largest_observed_vs_uniform"] = [round(obs, 4), round(float(exp), 4)]
    return {"N": N, "base": round(base, 5), "rates": {k: round(v, 5) for k, v in rates.items()}, "minus_base": {k: round(v - base, 5) for k, v in rates.items()},
            "within_applicable": {k: [round(v[0], 4), v[1]] for k, v in within.items()}, "a3_skipped_items": skipped, **extra}


def run_fresh(args):
    lid, N, seed = args
    a3, a4, im = mods()
    lin = survivors()[lid]
    st = stem(lid)
    return lid, {str(L): score(st, items(lin, L, N, seed, "rules"), ("a3", "a4", "im"), a3, a4, im, True) for L in range(7)}


def run_repro(args):
    lid, N = args
    a3, a4, im = mods()
    lin = survivors()[lid]
    st = stem(lid)
    out = {}
    for L in range(7):
        r4 = stream(17, "audit4-m1", "short", lin.id, str(L))
        r_own = stream(410302, "fix3-shortcuts", lid, str(L))
        r3 = stream(5, "audit3-m1", "short", lin.id, str(L))
        out[str(L)] = {"a4": score(st, [build_item(lin, L, r4, "A", f"x{i}") for i in range(N)], ("a4", "im"), a3, a4, im, False),
                       "own": score(st, [build_item(lin, L, r_own, "A", f"x{i}") for i in range(N)], ("im",), a3, a4, im, False),
                       "a3": score(st, [build_item(lin, L, r3, "A", f"x{i}") for i in range(N)], ("a3",), a3, a4, im, False)}
    return lid, out


if __name__ == "__main__":
    mode = sys.argv[1]
    ids = sorted(survivors())
    with get_context("spawn").Pool(14) as p:
        if mode == "fresh":
            N, seed, path = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
            res = dict(p.map(run_fresh, [(i, N, seed) for i in ids], chunksize=1))
            json.dump({"mode": mode, "N": N, "seed": seed, "label": "final-m1-a5/rules", "results": res}, open(path, "w"), indent=1, sort_keys=True)
        else:
            N, path = int(sys.argv[2]), sys.argv[3]
            res = dict(p.map(run_repro, [(i, N) for i in ids], chunksize=1))
            json.dump({"mode": mode, "N": N, "results": res}, open(path, "w"), indent=1, sort_keys=True)
    print("done", len(res))
