"""Independent re-implementation of the P7-B criterion layer (ADR-0014 sections 2, 7, 7a, 9) written
from the ADR text by the auditor role, standard library only, and two checks against the
implementer's ``p7b_analysis``:

  (1) TABLES: the ordered outcome table, the stream pairing, the decision classes and the
      recommendation table, over their complete input spaces;
  (2) RECOMPUTE: synthetic per-checkpoint simulation records for all 81 checkpoints and both streams
      in many scenarios (designed to reach every class, plus random ones); the implementer's
      ``analyze_streams`` output is compared with this file's own E, rho, rho_adj (exact rationals),
      non-degeneracy, counts, classes, tie-rule handling, PART_K, outcomes, decision classes and
      recommendation.

The criterion code below does not import arborlm. Only the comparison driver imports the
implementer's module (to call it). Synthetic records only; no trace or result is read.
"""

from __future__ import annotations

import itertools
import json
import random
import sys
from fractions import Fraction as F
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]

KINDS = ("flat", "fixed_tree", "learned_tree")
TREES = ("fixed_tree", "learned_tree")
PCOAX = tuple(f"L-PCOAX-{i}" for i in range(1, 6))
SETTINGS = {"primary": (2, 32), "confirmation": (8, 8)}
TIES = ("asc", "desc")
NULLS = ("null_1", "null_2", "null_3")
PAIRS = [(b, o, s) for b in (101, 102, 103) for o in (301, 302, 303) for s in (501, 502, 503)]
TB, FB, W10, INT, TD, DEG, INC = ("TREE MATERIALLY BETTER", "FLAT MATERIALLY BETTER", "WITHIN 10%",
                                   "INTERMEDIATE", "TIE-RULE DEPENDENT", "DEGENERATE", "INCOMPLETE")
REAL, NOTB = "REAL BRANCHES BETTER", "NOT BETTER"
O_UNRES, O_HIER, O_NB, O_NR = ("UNRESOLVED", "HIERARCHY-SPECIFIC ADVANTAGE",
                               "ADVANTAGE NOT SHOWN TO BE BRANCH-SPECIFIC", "NOT ROBUST")
O_FLAT, O_WITHIN, O_IT, O_IF = ("FLAT CO-ACCESS BETTER", "WITHIN 10% OF FLAT CO-ACCESS",
                                "INTERMEDIATE (tree-favouring)", "INTERMEDIATE (flat-favouring)")
OUTCOMES = (O_UNRES, O_HIER, O_NB, O_NR, O_FLAT, O_WITHIN, O_IT, O_IF)


def label(pair, kind):
    b, o, s = pair
    return f"b{b}-o{o}-{kind}-s{s}"


def mean(v):
    v = list(v)
    return sum(v, F(0)) / len(v)


# --------------------------------------------------------------------------------------------------
# the auditor's reading of the ADR
# --------------------------------------------------------------------------------------------------
def outcome(hb_p: str, hb_c: str, part_p: str, part_c: str, rho_asc_primary: F | None) -> str:
    """Section 7 ordered outcome table. TIE-RULE DEPENDENT counts as INTERMEDIATE."""
    if hb_p == DEG:
        return O_UNRES
    if hb_p == TB and hb_c == TB:
        return O_HIER if (part_p == REAL and part_c == REAL) else O_NB
    if hb_p == TB:
        return O_NR
    if hb_p == FB:
        return O_FLAT
    if hb_p == W10:
        return O_WITHIN
    return O_IT if (rho_asc_primary is not None and rho_asc_primary < 1) else O_IF


def pairing(a: str, b: str) -> str:
    if a == b and a != O_UNRES:
        return "REPLICATED"
    if a == b:
        return "UNRESOLVED ON BOTH STREAMS"
    if O_UNRES in (a, b):
        return "SINGLE-STREAM"
    return "NOT REPLICATED"


def decision(a: str, b: str) -> str:
    if a == O_HIER and b == O_HIER:
        return "S"
    if a == O_UNRES and b == O_UNRES:
        return "U"
    n = {O_WITHIN, O_FLAT, O_NB}
    if a in n and b in n:
        return "N"
    return "I"


def recommend(cf: str, cl: str) -> int:
    if "S" in (cf, cl):
        return 1
    if cf == cl == "N":
        return 2
    if cf == cl == "U":
        return 3
    return 4


def ols(points):
    """E = a + b x + d t by least squares (Cramer on the normal equations), exact."""
    n = F(len(points))
    sx = sum((x for x, t, y in points), F(0))
    st = sum((t for x, t, y in points), F(0))
    sy = sum((y for x, t, y in points), F(0))
    sxx = sum((x * x for x, t, y in points), F(0))
    sxt = sum((x * t for x, t, y in points), F(0))
    stt = sum((t * t for x, t, y in points), F(0))
    sxy = sum((x * y for x, t, y in points), F(0))
    sty = sum((t * y for x, t, y in points), F(0))
    M = [[n, sx, st], [sx, sxx, sxt], [st, sxt, stt]]
    rhs = [sy, sxy, sty]

    def det(m):
        return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
                - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))

    D = det(M)
    if D == 0:
        return None
    sol = []
    for col in range(3):
        Mc = [row[:] for row in M]
        for r in range(3):
            Mc[r][col] = rhs[r]
        sol.append(det(Mc) / D)
    a, b, d = sol
    xbar = sx / n
    level = a + b * xbar
    if level <= 0:
        return None
    return (level + d) / level


class Rec:
    def __init__(self, records):
        self.r = records

    def m(self, lb, stream, layout, R, C, tie):
        e = self.r[lb]["record"]["streams"][stream][f"{layout}|R{R}"]["by_c"][str(C)][tie]
        q = self.r[lb]["record"]["queries"]
        return F(e["misses_warm"] - e["first_touch_warm"], q - q // 2)

    def null(self, lb, layout, R, C, tie):
        return mean(self.m(lb, s, layout, R, C, tie) for s in NULLS)

    def x(self, lb):
        return F(self.r[lb]["record"]["evaluation_counts"]["entropy_nats"])


def counts_hold(cand: dict, ref: dict) -> bool:
    cells = sum(1 for p in PAIRS if cand[p] < ref[p])
    parents = 0
    for b in (101, 102, 103):
        for o in (301, 302, 303):
            mem = [p for p in PAIRS if p[:2] == (b, o)]
            if mean(cand[p] for p in mem) < mean(ref[p] for p in mem):
                parents += 1
    return cells >= 22 and parents >= 8


def one_tie(rec: Rec, kind: str, R: int, C: int, tie: str, tl: str, fl: str) -> dict:
    den = {k: {p: rec.null(label(p, k), "L-FREQ", R, C, tie) for p in PAIRS} for k in ("flat", kind)}
    num = {"flat": {p: rec.m(label(p, "flat"), "actual", fl, R, C, tie) for p in PAIRS},
           kind: {p: rec.m(label(p, kind), "actual", tl, R, C, tie) for p in PAIRS}}
    ok = (mean(den["flat"].values()) >= F(1, 20) and mean(den[kind].values()) >= F(1, 100)
          and min([*den["flat"].values(), *den[kind].values()]) >= F(1, 200)
          and mean(num["flat"].values()) >= F(1, 100) and mean(num[kind].values()) >= F(1, 100))
    if not ok:
        return {"status": DEG}
    ef = {p: num["flat"][p] / den["flat"][p] for p in PAIRS}
    et = {p: num[kind][p] / den[kind][p] for p in PAIRS}
    rho = mean(et.values()) / mean(ef.values())
    pts = [(rec.x(label(p, "flat")), F(0), ef[p]) for p in PAIRS] + \
          [(rec.x(label(p, kind)), F(1), et[p]) for p in PAIRS]
    radj = ols(pts)
    tree_fav, flat_fav = counts_hold(et, ef), counts_hold(ef, et)
    if radj is None:
        cls = INT
    elif rho <= F(4, 5) and radj <= F(4, 5) and tree_fav:
        cls = TB
    elif rho >= F(5, 4) and radj >= F(5, 4) and flat_fav:
        cls = FB
    elif F(9, 10) <= rho <= F(11, 10) and F(9, 10) <= radj <= F(11, 10):
        cls = W10
    else:
        cls = INT
    return {"status": "OK", "class": cls, "rho": rho, "rho_adj": radj}


def comparison(rec, kind, R, C, tl, fl):
    by = {t: one_tie(rec, kind, R, C, t, tl, fl) for t in TIES}
    if any(v["status"] == DEG for v in by.values()):
        return DEG, by
    classes = {v["class"] for v in by.values()}
    return (classes.pop() if len(classes) == 1 else TD), by


def part(rec, kind, R, C):
    labels_ = ("L-BCOAX", *PCOAX)
    res = {}
    for tie in TIES:
        dens = {L: {p: rec.null(label(p, kind), L, R, C, tie) for p in PAIRS} for L in labels_}
        if any(min(d.values()) < F(1, 200) or mean(d.values()) < F(1, 100) for d in dens.values()):
            return DEG
        S = {L: {p: rec.m(label(p, kind), "actual", L, R, C, tie) / dens[L][p] for p in PAIRS} for L in labels_}
        sb = S["L-BCOAX"]
        sp = {p: mean(S[L][p] for L in PCOAX) for p in PAIRS}
        agg = mean(sb.values()) <= F(4, 5) * mean(sp.values()) and counts_hold(sb, sp)
        each = all(mean(sb.values()) <= F(4, 5) * mean(S[L].values()) for L in PCOAX)
        res[tie] = agg and each
    return REAL if all(res.values()) else NOTB


def criteria(records: dict) -> dict:
    rec = Rec(records)
    out = {}
    for kind in TREES:
        hb = {n: comparison(rec, kind, *rc, "L-BCOAX", "L-COAX") for n, rc in SETTINGS.items()}
        hu = {n: comparison(rec, kind, *rc, "L-COAX", "L-COAX")[0] for n, rc in SETTINGS.items()}
        pk = {n: part(rec, kind, *rc) for n, rc in SETTINGS.items()}
        asc = hb["primary"][1]["asc"]
        rho_asc = asc.get("rho") if asc["status"] == "OK" else None
        o = outcome(hb["primary"][0], hb["confirmation"][0], pk["primary"], pk["confirmation"], rho_asc)
        out[kind] = {
            "HB": {n: v[0] for n, v in hb.items()},
            "HU": hu,
            "PART": pk,
            "outcome": o,
            "rho": {f"{n}|{t}": (None if v[1][t]["status"] != "OK" else v[1][t]["rho"])
                    for n, v in hb.items() for t in TIES},
            "rho_adj": {f"{n}|{t}": (None if v[1][t]["status"] != "OK" else v[1][t]["rho_adj"])
                        for n, v in hb.items() for t in TIES},
        }
    return out


# --------------------------------------------------------------------------------------------------
# synthetic records
# --------------------------------------------------------------------------------------------------
def make_records(g: random.Random, scenario: str) -> dict:
    Q = 32768
    counted = Q - Q // 2
    recs = {}
    for p in PAIRS:
        for k in KINDS:
            tree = k != "flat"
            streams = {s: {} for s in ("actual", *NULLS)}
            base = {"flat": 3.2, "fixed_tree": 2.2, "learned_tree": 1.7}[k]
            if scenario == "degenerate_primary":
                base = 0.002
            for (name, (R, C)) in SETTINGS.items():
                for L in ("L-FREQ", "L-COAX", "L-NCOAX", "L-BCOAX", *PCOAX):
                    if L == "L-BCOAX" and not tree:
                        continue
                    for s in ("actual", *NULLS):
                        by = {}
                        for tie in TIES:
                            if s == "actual":
                                if scenario == "hierarchy":
                                    fac = {"L-BCOAX": 0.45, "L-COAX": 0.8 if tree else 0.85}.get(L, 1.0)
                                    if L in PCOAX:
                                        fac = 1.0
                                elif scenario == "tie_dependent" and tree and L == "L-BCOAX":
                                    fac = 0.5 if tie == "asc" else 0.95
                                elif scenario == "flat_better" and tree and L == "L-BCOAX":
                                    fac = 1.6
                                elif scenario == "within":
                                    fac = 0.8 * g.uniform(0.98, 1.02)
                                elif scenario == "confirm_only_degenerate" and name == "confirmation":
                                    fac = 0.0005
                                else:
                                    fac = g.uniform(0.6, 1.2)
                            else:
                                fac = 1.0 if L == "L-FREQ" else (g.uniform(1.0, 1.4) if L in PCOAX else g.uniform(0.95, 1.1))
                            if scenario == "confirm_only_degenerate" and name == "confirmation" and s != "actual":
                                fac = 1.0
                            cap = max(0, int(base * fac * counted * g.uniform(0.97, 1.03)))
                            by[tie] = {"misses_warm": cap + 50, "first_touch_warm": 50,
                                       "misses_all": cap + 300, "first_touch_all": 300,
                                       "ctx_q": [0, 1, 2, 3, 4, 5, 6]}
                        # attempt 1 left "stats" empty; the implementer's descriptive tables need it
                        streams[s][f"{L}|R{R}"] = {"by_c": {str(C): by}, "stats": {
                            "hist": [0, 0, 0, 0, 0, 0, 0, Q], "pages_sum": 8 * Q,
                            "distinct_stream": 400, "distinct_first_half": 350}}
            recs[label(p, k)] = {
                "outcome": "completed",
                "record": {"complete": True, "queries": Q, "kind": k,
                           "evaluation_counts": {"entropy_nats": g.uniform(5.0, 6.5) - (0.4 if tree else 0.0),
                                                 "unique_selected_slots": 500, "effective_slots": 300.0},
                           "streams": streams},
            }
    return recs


def main() -> int:
    sys.path.insert(0, str(REPO / "src"))
    from arborlm import p7b_analysis as A

    report: dict = {"tables": {}, "recompute": []}
    # (1) tables over the complete input space
    hb_classes = (TB, FB, W10, INT, TD, DEG)
    part_labels = (REAL, NOTB, DEG)
    bad = []
    n = 0
    for hp, hc, pp, pc, rho in itertools.product(hb_classes, hb_classes, part_labels, part_labels,
                                                  (F(3, 4), F(1), F(5, 4))):
        rho_exact = f"{rho.numerator}/{rho.denominator}"
        hbp = {"class": hp, "by_tie": {"asc": ({} if hp == DEG else {"rho_exact": rho_exact})}}
        theirs = A.outcome_for(hbp, {"class": hc}, pp, pc)
        mine = outcome(hp, hc, pp, pc, None if hp == DEG else rho)
        n += 1
        if theirs != mine:
            bad.append({"in": [hp, hc, pp, pc, str(rho)], "implementer": theirs, "auditor": mine})
    report["tables"]["outcome_cases"] = n
    report["tables"]["outcome_mismatches"] = bad
    pb = [(a, b, A.stream_pairing(a, b)["pairing"], pairing(a, b)) for a in OUTCOMES for b in OUTCOMES
          if A.stream_pairing(a, b)["pairing"] != pairing(a, b)]
    db = [(a, b) for a in OUTCOMES for b in OUTCOMES if A.decision_class(a, b) != decision(a, b)]
    rb = [(a, b) for a in "SUNI" for b in "SUNI" if A.recommendation(a, b)["row"] != recommend(a, b)]
    report["tables"].update(pairing_cases=64, pairing_mismatches=pb, decision_cases=64,
                            decision_mismatches=db, recommendation_cases=16, recommendation_mismatches=rb)
    # which outcome pairs give S
    report["tables"]["pairs_giving_S"] = [(a, b) for a in OUTCOMES for b in OUTCOMES if decision(a, b) == "S"]
    # (2) recompute on synthetic records
    scenarios = ["hierarchy", "tie_dependent", "flat_better", "within", "degenerate_primary",
                 "confirm_only_degenerate"] + [f"random_{i}" for i in range(14)]
    total_mismatch = 0
    seen_outcomes: set = set()
    for i, sc in enumerate(scenarios):
        g = random.Random(7000 + i)
        streams = {"A": make_records(g, sc), "B": make_records(g, sc)}
        theirs = A.analyze_streams(streams)
        mismatches = []
        mine_all = {}
        for st in ("A", "B"):
            mine = criteria(streams[st])
            mine_all[st] = mine
            tk = theirs["per_stream"][st]["tree_kinds"]
            for kind in TREES:
                t = tk[kind]
                for key in ("HB", "HU", "PART"):
                    if t[key] != mine[kind][key]:
                        mismatches.append((st, kind, key, t[key], mine[kind][key]))
                if t["outcome"] != mine[kind]["outcome"]:
                    mismatches.append((st, kind, "outcome", t["outcome"], mine[kind]["outcome"]))
                seen_outcomes.add(mine[kind]["outcome"])
                for sname in SETTINGS:
                    hb = t["settings"][sname]["HB"]["by_tie"]
                    for tie in TIES:
                        r_mine = mine[kind]["rho"][f"{sname}|{tie}"]
                        ra_mine = mine[kind]["rho_adj"][f"{sname}|{tie}"]
                        r_t = hb[tie].get("rho_exact")
                        ra_t = hb[tie].get("rho_adj_exact")
                        if (None if r_mine is None else f"{r_mine.numerator}/{r_mine.denominator}") != r_t:
                            mismatches.append((st, kind, sname, tie, "rho", r_t, str(r_mine)))
                        if (None if ra_mine is None else f"{ra_mine.numerator}/{ra_mine.denominator}") != ra_t:
                            mismatches.append((st, kind, sname, tie, "rho_adj", ra_t, str(ra_mine)))
        for kind in TREES:
            a, b = mine_all["A"][kind]["outcome"], mine_all["B"][kind]["outcome"]
            if theirs["combined"]["tree_kinds"][kind]["decision_class"] != decision(a, b):
                mismatches.append(("combined", kind, "decision"))
        rec_mine = recommend(decision(mine_all["A"]["fixed_tree"]["outcome"], mine_all["B"]["fixed_tree"]["outcome"]),
                             decision(mine_all["A"]["learned_tree"]["outcome"], mine_all["B"]["learned_tree"]["outcome"]))
        if theirs["combined"]["recommendation"]["row"] != rec_mine:
            mismatches.append(("combined", "recommendation", theirs["combined"]["recommendation"]["row"], rec_mine))
        total_mismatch += len(mismatches)
        report["recompute"].append({
            "scenario": sc,
            "outcomes": {st: {k: mine_all[st][k]["outcome"] for k in TREES} for st in ("A", "B")},
            "HB": {st: {k: mine_all[st][k]["HB"] for k in TREES} for st in ("A", "B")},
            "PART": {st: {k: mine_all[st][k]["PART"] for k in TREES} for st in ("A", "B")},
            "recommendation_row": rec_mine,
            "mismatches": [list(map(str, m)) for m in mismatches],
        })
    report["recompute_total_mismatches"] = total_mismatch
    report["outcomes_reached_in_recompute"] = sorted(seen_outcomes)
    ok = (not bad and not pb and not db and not rb and total_mismatch == 0)
    print(json.dumps(report, indent=1, default=str))
    print("ANALYSIS INDEPENDENT CHECK", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
