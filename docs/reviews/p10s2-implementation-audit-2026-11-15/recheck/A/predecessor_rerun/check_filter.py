"""Audit A, check 4: the precision filter of ADR-0022 section 5.3 recomputed independently (Wilson bound by solving the score-test quadratic,
brute-force selection over the registered grid with the ADR's tie-break) and compared with studies/p10s2/filtering.py on synthetic outputs.
Written by the auditor (Claude Opus 5.5). Run from the pinned tree:  <python> <this file>
"""

import math
import random
import sys
from pathlib import Path

PIN = Path.cwd()
sys.path.insert(0, str(PIN))
sys.path.insert(0, str(PIN / "src"))
from studies.p10s2 import filtering as F  # noqa: E402
from studies.p10s2.text import chrf_item, normalize, wilson  # noqa: E402

out: list[str] = []


def say(s: str) -> None:
    out.append(s)
    print(s)


Z = 1.959963984540054  # the 0.975 normal quantile


def my_wilson_lower(k: int, n: int) -> float:
    """Lower root of (p - phat)^2 = z^2 p (1 - p) / n, solved as a quadratic in p (independent of the centre/half-width form)."""
    if n == 0:
        return 0.0
    ph = k / n
    a = 1 + Z * Z / n
    b = -(2 * ph + Z * Z / n)
    c = ph * ph
    disc = b * b - 4 * a * c
    return max(0.0, (-b - math.sqrt(max(disc, 0.0))) / (2 * a))


worst = 0.0
for n in range(1, 601):
    for k in range(0, n + 1):
        worst = max(worst, abs(my_wilson_lower(k, n) - wilson(k, n)[0]))
say(f"[wilson] max |lower bound difference| over n = 1..600, all k: {worst:.3e}")
# the ADR's sentence: a measured 0.90 at 150 items has a 95% interval of about 0.84-0.94; at 500 about 0.87-0.92
say(f"[wilson] 135/150 -> {wilson(135, 150)}; 450/500 -> {wilson(450, 500)}")
# smallest k at which the lower bound reaches 0.90, for a few n (what the fit demands)
for n in (50, 100, 150, 300, 500):
    kmin = next(k for k in range(n + 1) if wilson(k, n)[0] >= 0.90)
    say(f"[wilson] n = {n}: lower bound >= 0.90 needs k >= {kmin} (point precision {kmin / n:.3f})")

# grid
g = F.settings_grid()
taus = sorted({s.tau for s in g})
say(f"[grid] {len(g)} settings; tau {taus[0]}..{taus[-1]} step 0.05: {[round(t, 2) for t in taus] == [round(-0.05 * i, 2) for i in range(12, 0, -1)]}; ranges {sorted({(s.rho1, s.rho2) for s in g})}")

# synthetic outputs; brute force with the ADR's rule
rng = random.Random(7)  # the auditor's own generator


def make(nitems: int, shift: float) -> tuple[list, list]:
    outs, refs = [], []
    for k in range(nitems):
        src = " ".join(f"w{rng.randrange(40)}" for _ in range(rng.randrange(3, 9)))
        good = rng.random() < 0.93
        ref = " ".join(f"r{w[1:]}" for w in src.split())
        txt = ref if good else " ".join(f"z{rng.randrange(99)}" for _ in range(rng.randrange(1, 14)))
        score = -abs(rng.gauss(0.12 if good else 0.45, 0.12)) + shift
        outs.append(F.Output(src, txt, round(score, 3)))
        refs.append([ref])
    return outs, refs


def brute(outs, refs):
    best = None
    for s in g:
        acc = [(o, r) for o, r in zip(outs, refs) if (normalize(o.source) and o.score == o.score and o.score >= s.tau and s.rho1 <= len(normalize(o.text).split()) / len(normalize(o.source).split()) <= s.rho2 and normalize(o.text) != normalize(o.source))]
        n = len(acc)
        if n == 0:
            continue
        k = sum(1 for o, r in acc if chrf_item(o.text, r) >= 0.60)
        if my_wilson_lower(k, n) < 0.90:
            continue
        key = (n, s.tau, -(s.rho2 - s.rho1))
        if best is None or key > best[0]:
            best = (key, s, n, k)
    return best


agree = 0
trials = 300
for t in range(trials):
    outs, refs = make(500, rng.choice([0.0, 0.05, -0.05]))
    b = brute(outs, refs)
    fit = F.fit_filter(outs, refs)
    if (b is None and fit.setting is None) or (b is not None and fit.setting == b[1] and fit.accepted == b[2]):
        agree += 1
say(f"[fit] implementation agrees with the brute-force rule on {agree}/{trials} synthetic Q_fit sets")

# tie-break probes: constructed so that two settings accept the same set
outs = [F.Output("a b c d", "x y z w", -0.07) for _ in range(200)]
refs = [["x y z w"]] * 200
fit = F.fit_filter(outs, refs)
say(f"[tie] every setting with tau <= -0.10 accepts all 200 (equal share) -> chosen {fit.setting} (ADR: larger tau, then the narrower range -> tau -0.10, [0.6, 1.6])")
outs2 = [F.Output("a b c d", "x y z w q", -0.02) for _ in range(200)]  # ratio 1.25: inside both ranges
fit2 = F.fit_filter(outs2, [["x y z w q"]] * 200)
say(f"[tie] all settings accept all -> chosen {fit2.setting} (ADR: tau -0.05, [0.6, 1.6])")
# non-finite scores
say(f"[score] NaN accepted: {F.accepts(F.Output('a b c', 'x y z', float('nan')), F.FilterSetting(-0.6, 0.5, 2.0))}; +inf accepted: {F.accepts(F.Output('a b c', 'x y z', float('inf')), F.FilterSetting(-0.05, 0.5, 2.0))}; -inf accepted: {F.accepts(F.Output('a b c', 'x y z', float('-inf')), F.FilterSetting(-0.6, 0.5, 2.0))}")
# check on Q_check
c = F.check_filter(F.FilterSetting(-0.1, 0.6, 1.6), [F.Output("a b c", "x y z", -0.01)] * 150, [["x y z"]] * 135 + [["q"]] * 15, 150)
say(f"[check] 135/150 correct at the bar: ok = {c['ok']} (precision {c['precision']:.3f}); 149 accepted: ok = {F.check_filter(F.FilterSetting(-0.1, 0.6, 1.6), [F.Output('a b c', 'x y z', -0.01)] * 149, [['x y z']] * 149, 150)['ok']}")
Path(__file__).with_suffix(".out.txt").write_text("\n".join(out) + "\n")
