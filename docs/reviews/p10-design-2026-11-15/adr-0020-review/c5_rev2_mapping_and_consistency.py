"""Confirmation of ADR-0020 revision 2.

Part 1: re-enumerate the reduced mapping (§3.2 rule against the §3.3 table) over the same P9-II
record space as c2 (P9-II model functions are re-used from the auditor's own c2 script).
Part 2: the lead's cross-study consistency rule (ruling 1) against the auditor's per-size rule,
enumerated over P9-II's and S0's draw-level outcomes at 4,096 and 16,384, with NOT_EVALUATED draws.
Part 3: bounds and the revision-2 projection / headroom arithmetic.

Usage: python3 -I c5_rev2_mapping_and_consistency.py   (run from the review folder)
"""

import itertools
import os
import sys
from collections import Counter
from math import comb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c2_mapping_enumeration as c2  # the auditor's own model of ADR-0019 rev4 (P9-II)

LABEL_FREE_C4 = {"A4", "A5-C", "A5-D"}


# ------------------------------------------------------------------ Part 1
def c4_rule(outcome, st2, carried):
    """ADR-0020 rev2 §3.2 (calibration record assumed present)."""
    if outcome in ("ENGINEERING_FAIL", "INCOMPLETE", "NOT_INTERPRETED"):
        return None
    if st2 != "COMPLETE":
        return None
    return carried if carried in LABEL_FREE_C4 else None


def c4_table(outcome, st2, carried, cls16):
    """ADR-0020 rev2 §3.3, literal reading."""
    if outcome == "ADDRESSING-RELIABLE":
        return carried if carried in LABEL_FREE_C4 else None
    if outcome == "ANSWER-ONLY RELIABLE":
        if st2 != "COMPLETE":
            return None
        if carried == "A0":
            return None
        if carried in LABEL_FREE_C4:
            # row says "A0 not RELIABLE or LM-flagged at 16,384, carried arm A5-C, A5-D or A4"
            return carried
        return None
    if outcome == "ADDRESSING-RELIABLE AT 4,096 ONLY":
        return "UNLISTED" if carried in LABEL_FREE_C4 else None
    return None


def part1():
    n = 0
    dis = Counter()
    c4_by_outcome = Counter()
    row5_carried = Counter()
    for combo in itertools.product(c2.CLS4, repeat=6):
        cls4 = dict(zip(c2.ARMS, combo))
        for nc4 in (False, True):
            runs, adv = c2.p9ii_advanced(cls4, nc4)
            for st2 in (["COMPLETE", "BUDGET", "INCOMPLETE", "NE"] if runs else ["NORUN"]):
                sup_adv = any(x in c2.SUP for x in adv)
                for nc16 in ((False, True) if sup_adv and st2 in ("COMPLETE", "INCOMPLETE") else (False,)):
                    it = (dict(zip(adv, v)) for v in itertools.product(c2.CLS16, repeat=len(adv))) \
                        if st2 == "COMPLETE" else iter([{}] + ([{x: "R"} for x in adv] if st2 == "INCOMPLETE" else []))
                    for cls16 in it:
                        n += 1
                        out = c2.p9ii_outcome(False, cls4, nc4, nc16, st2, cls16)
                        carried = c2.p9ii_carried(cls4, nc4, nc16, st2, cls16)
                        r = c4_rule(out, st2, carried)
                        t = c4_table(out, st2, carried, cls16)
                        if out == "ADDRESSING-RELIABLE AT 4,096 ONLY":
                            row5_carried[carried] += 1
                        if r != t:
                            dis[(out, str(r), str(t))] += 1
                        if r:
                            c4_by_outcome[(out, r)] += 1
    print(f"Part 1: {n} P9-II records enumerated")
    print("  rule-vs-table disagreements:", dict(dis) if dis else "none")
    print("  C4 present, by P9-II outcome:")
    for k, v in sorted(c4_by_outcome.items()):
        print(f"    {v:>8} {k}")
    print("  carried arm under 'ADDRESSING-RELIABLE AT 4,096 ONLY' (table says 'nothing is carried'):",
          dict(row5_carried))


# ------------------------------------------------------------------ Part 2
def cp_lower(k, n, alpha=0.05):
    if k == 0:
        return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(200):
        m = (lo + hi) / 2
        t = sum(comb(n, j) * m**j * (1 - m) ** (n - j) for j in range(k, n + 1))
        lo, hi = (m, hi) if t < alpha else (lo, m)
    return (lo + hi) / 2


def p9ii_class(failed_cells_per_draw, n_ne, size):
    """ADR-0019 rev4 §8.4 at Stage 1 (8 draws x 2) or Stage 2 (4 draws x 2), LM flags ignored."""
    evaluated_cells = 2 * len(failed_cells_per_draw)
    if size == 4096 and evaluated_cells < 14:
        return "NE"
    if size == 16384 and n_ne > 0:
        return "NE"
    failed = sum(failed_cells_per_draw)
    succ = evaluated_cells - failed
    if failed <= 1:
        return "R"
    if succ >= (4 if size == 4096 else 2):
        return "U"
    return "F"


def part2():
    print("\nPart 2: cross-study consistency (S0 RELIABLE assumed; S0 has 10 draws x 2 seeds)")
    # S0 RELIABLE => at most one failed cell among evaluated cells, at most one NE draw.
    s0_states = []
    for ne in (0, 1):
        ev = 10 - ne
        for f in (0, 1):  # failed draws (= failed cells, at most 1)
            s0_states.append((ev, f))
    rows = []
    for size, ndraw in ((4096, 8), (16384, 4)):
        seen = Counter()
        for ne in range(0, 2 if size == 4096 else 2):
            ev = ndraw - ne
            for pattern in itertools.product((0, 1, 2), repeat=ev):  # failed cells per evaluated draw
                cls = p9ii_class(list(pattern), ne, size)
                if cls == "NE":
                    continue
                p_fail_draws = sum(1 for x in pattern if x > 0)
                for s_ev, s_f in s0_states:
                    pooled_n = ev + s_ev
                    pooled_ok = pooled_n - (p_fail_draws + s_f)
                    lead = (cls == "R") or (pooled_n == 18 and pooled_ok >= 16)   # literal ruling (4,096 only)
                    lead_ambiguous = (cls != "R") and pooled_n != 18
                    mine = (p_fail_draws + s_f) <= 2
                    key = (size, cls, ev, p_fail_draws, s_ev, s_f, pooled_ok, pooled_n, lead, lead_ambiguous, mine)
                    seen[key] += 1
        print(f"  size {size}: P9-II class / evaluated draws / failed draws | S0 evaluated / failed | pooled ok/n "
              f"| lead's rule | ambiguous | auditor's rule (pooled failed draws <= 2)")
        for key in sorted(set(seen)):
            size_, cls, ev, pf, s_ev, s_f, ok, n, lead, amb, mine = key
            flag = "  <-- differs" if (lead != mine and not amb) else ("  <-- lead's rule undefined" if amb else "")
            print(f"    P9-II {cls} {ev}d {pf}f | S0 {s_ev}d {s_f}f | {ok}/{n} (bound {cp_lower(ok, n):.3f}) | "
                  f"{'Q' if lead else '-'} | {'?' if amb else ' '} | {'Q' if mine else '-'}{flag}")
    print("\n  Note: at 16,384 the lead's ruling reads only P9-II's class at 4,096, so an arm that P9-II classed")
    print("  FAILS at 16,384 (e.g. 0 of 4 draws) qualifies if it was RELIABLE at 4,096 in P9-II and RELIABLE in S0.")
    print(f"  Example pooled 10/14 at 16,384: bound {cp_lower(10, 14):.3f}; 12/14: {cp_lower(12, 14):.3f}; "
          f"16/18: {cp_lower(16, 18):.3f}; 15/17: {cp_lower(15, 17):.3f}; 11/13: {cp_lower(11, 13):.3f}")


# ------------------------------------------------------------------ Part 3
def part3():
    print("\nPart 3: bounds and projections of revision 2")
    for k, n in ((10, 10), (9, 10), (9, 9), (8, 9), (8, 10), (3, 3), (18, 18), (17, 18), (14, 14), (13, 14)):
        print(f"  {k}/{n}: {cp_lower(k, n):.3f}")
    R = {"fastest": (0.008, 0.013, 0.035), "W7": (0.0098, 0.0141, 0.0531), "slowest": (0.0112, 0.0195, 0.0619)}
    def h(cells, r):
        return sum(n * u * {4096: r[0], 16384: r[1], 65536: r[2]}[s] for n, u, s in cells) / 3600
    q1_4 = [(100, 8192, 4096), (30, 32768, 4096), (100, 32768, 16384)]
    q1_3 = [(80, 8192, 4096), (20, 32768, 4096), (80, 32768, 16384)]
    wx = [(10, 8192, 4096), (10, 32768, 16384)]
    probe = [(6, 131072, 65536)]
    cut3_4 = [(100, 8192, 4096), (30, 32768, 4096), (50 + 20, 32768, 16384)]  # 8K/16K: 4 arms x10 + A6,A7 x10... see below
    print(f"  cells: Q1 four arms {sum(c[0] for c in q1_4)}, three arms {sum(c[0] for c in q1_3)}, WX 20, probe 6, check 3")
    for name, r in R.items():
        a, b, c, d = h(q1_4, r), h(q1_3, r), h(wx, r), h(probe, r)
        six = a / 6 + c / 6 + d / 6 + 0.8   # probe: six cells = one round = summed/6 (attempt-1 bug used d)
        print(f"  {name:8} Q1(4) {a:5.2f}  Q1(3) {b:5.2f}  WX {c:4.2f}  probe {d:5.2f} | six workers {six:4.2f} h,"
              f" doubled {2*six:5.2f} h, left of 16 h {16-2*six:5.2f} h ({(16-2*six)/16:.0%} of the cap)")
    # cut 3: second seed dropped at 8K/16K -> learned arms 10 cells each there; references unchanged (20)
    q1_4_cut3 = [(100, 8192, 4096), (30, 32768, 4096), (4 * 10 + 20, 32768, 16384)]
    for name, r in R.items():
        print(f"  {name:8} after cuts 1+2+3: Q1(4) six workers {h(q1_4_cut3, r)/6 + 0.8:4.2f} h, doubled {2*(h(q1_4_cut3, r)/6 + 0.8):5.2f} h")
    # what multiple of the slowest rate can the uncut configuration absorb?
    r = R["slowest"]
    base = h(q1_4, r) / 6 + h(wx, r) / 6 + h(probe, r) / 6
    print(f"  slowest rates: training share of the six-worker time {base:4.2f} h; 2x(base*m + 0.8) <= 16 holds for m <= {(8 - 0.8) / base:.3f}")
    base_nop = h(q1_4, r) / 6 + h(wx, r) / 6
    print(f"  without the probe (cut 2 applied): m <= {(8 - 0.8) / base_nop:.3f}; Q1(4) alone: m <= {(8 - 0.8) / (h(q1_4, r) / 6):.3f}")


if __name__ == "__main__":
    part1()
    part2()
    part3()
