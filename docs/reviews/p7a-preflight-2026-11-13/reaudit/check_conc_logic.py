"""Re-audit check (synthetic only): the section 7 criteria and outcome table, with ADR-0013 section 14
item 9, as implemented in arborlm.p7a_analysis.criteria (the code under audit, called as a black box),
against the auditor's own implementation written from the ADR text. No arborlm code is used to
compute the expected outcome. Random fabricated warm-capacity-miss counts are drawn near the floors
(0.05, 0.01), the 0.80 ratio and the 22/27 and 8/9 counts, so that every branch is exercised.

Run (repo root):
  uv run --locked --extra pilot python docs/reviews/p7a-preflight-2026-11-13/reaudit/check_conc_logic.py
"""

import json
import random
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

from arborlm import p7a_analysis as an  # subject under test only

HERE = Path(__file__).resolve().parent
QUERIES = 200
COUNTED = QUERIES - QUERIES // 2  # 100: floors are 5/100 (flat) and 1/100 (tree)
B, O, S = (101, 102, 103), (301, 302, 303), (501, 502, 503)
PAIRS = [(b, o, s) for b in B for o in O for s in S]
KINDS = ("flat", "fixed_tree", "learned_tree")
RS, CS = (1, 2, 8, 32, 128, 512), (8, 16, 32, 64, 128)
RAND = ("L-RAND-91101", "L-RAND-91102", "L-RAND-91103")
FM = ("freq_matched_1", "freq_matched_2", "freq_matched_3")


# --- the auditor's reading of section 7 + item 9 ---------------------------------------------------
def mean(xs: list[Fraction]) -> Fraction:
    return sum(xs, Fraction(0)) / len(xs)


def adv(ref: dict, cand: dict) -> bool:
    if not mean(list(cand.values())) <= Fraction(4, 5) * mean(list(ref.values())):
        return False
    if sum(cand[p] < ref[p] for p in PAIRS) < 22:
        return False
    lower = 0
    for b in B:
        for o in O:
            members = [(b, o, s) for s in S]
            lower += mean([cand[p] for p in members]) < mean([ref[p] for p in members])
    return lower >= 8


def setting(m: dict, kind: str, r: int, c: int) -> tuple[str, str]:
    flat = {p: m[("flat", "actual", "L-FREQ", r, c)][p] for p in PAIRS}
    tree = {p: m[(kind, "actual", "L-FREQ", r, c)][p] for p in PAIRS}
    if not (mean(list(flat.values())) >= Fraction(1, 20) and mean(list(tree.values())) >= Fraction(1, 100)):
        return "DEGENERATE", "DEGENERATE"
    lru = "HOLDS" if adv(flat, tree) else "FAILS"
    fflat = {p: mean([m[("flat", s, "L-FREQ", r, c)][p] for s in FM]) for p in PAIRS}
    ftree = {p: mean([m[(kind, s, "L-FREQ", r, c)][p] for s in FM]) for p in PAIRS}
    if mean(list(fflat.values())) < Fraction(1, 20):
        conc = "DEGENERATE"
    else:
        conc = "HOLDS" if adv(fflat, ftree) else "FAILS"
    return lru, conc


def expected_outcome(m: dict, kind: str) -> tuple[str, str, str]:
    lru, conc = setting(m, kind, 2, 32)
    if lru == "DEGENERATE":
        return lru, conc, "UNRESOLVED"
    if lru == "FAILS":
        return lru, conc, "NO ADVANTAGE"
    if conc == "HOLDS":
        return lru, conc, "CONCENTRATION-ONLY"
    if conc == "DEGENERATE":
        return lru, conc, "UNSPECIFIED"
    robust = any(
        setting(m, kind, r, c) == ("HOLDS", "FAILS")
        for r in RS
        for c in CS
        if r <= 8 and (r, c) != (2, 32)
    )
    return lru, conc, "STRUCTURAL ADVANTAGE, " + ("robust" if robust else "not robust")


# --- random fabricated study ------------------------------------------------------------------------
def draw(rng: random.Random) -> dict:
    """m[(kind, stream, layout, R, C)][pair] as Fractions with denominator COUNTED (integers 0..)."""
    m: dict = {}
    regime = rng.choice(["near_floor", "near_ratio", "zero_null", "wide", "tiny_tree"])
    for r in RS:
        for c in CS:
            base_flat = {"near_floor": rng.choice([4, 5, 6]), "near_ratio": 10, "zero_null": 8,
                         "wide": rng.randint(0, 20), "tiny_tree": rng.choice([5, 6, 10])}[regime]
            ratio = rng.choice([0.5, 0.75, 0.8, 0.85, 1.0, 1.2])
            fm_flat = {"zero_null": rng.choice([0, 0, 4, 5]), "near_floor": rng.choice([4, 5, 6])}.get(
                regime, rng.randint(0, 20))
            fm_ratio = rng.choice([0.5, 0.8, 0.85, 1.0, 1.3, 0.0])
            for kind in KINDS:
                for stream in ("actual", *FM):
                    layouts = ("L-ID", "L-FREQ", *RAND) if stream == "actual" else ("L-ID", "L-FREQ")
                    for layout in layouts:
                        vals = {}
                        for p in PAIRS:
                            if stream == "actual":
                                f = base_flat + rng.choice([-1, 0, 0, 1])
                                t = round(base_flat * ratio) + rng.choice([-1, 0, 0, 1])
                                if regime == "tiny_tree":
                                    t = rng.choice([0, 0, 1, 2])
                            else:
                                f = fm_flat + rng.choice([-1, 0, 1])
                                t = round(fm_flat * fm_ratio) + rng.choice([-1, 0, 1])
                            v = f if kind == "flat" else t
                            vals[p] = Fraction(max(0, v), COUNTED)
                        m[(kind, stream, layout, r, c)] = vals
    return m


def records_from(m: dict) -> dict:
    out = {}
    for b in B:
        for o in O:
            for s in S:
                p = (b, o, s)
                for kind in KINDS:
                    label = f"b{b}-o{o}-{kind}-s{s}"
                    streams: dict = {}
                    for (k, stream, layout, r, c), vals in m.items():
                        if k != kind:
                            continue
                        group = streams.setdefault(stream, {}).setdefault(f"{layout}|R{r}", {"by_c": {}})
                        n = vals[p] * COUNTED
                        assert n.denominator == 1
                        group["by_c"][str(c)] = {"misses_warm": 1000 + int(n), "first_touch_warm": 1000}
                    out[label] = {"label": label, "queries": QUERIES,
                                  "record": {"complete": True, "streams": streams}}
    return out


def main() -> int:
    rng = random.Random(91999)
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    tally: Counter = Counter()
    mismatches = []
    for i in range(n):
        m = draw(rng)
        crit = an.criteria(an.Study(records_from(m)))
        for kind in ("fixed_tree", "learned_tree"):
            exp = expected_outcome(m, kind)
            got_entry = crit["tree_kinds"][kind]
            got = (got_entry["LRU"], got_entry["CONC"], got_entry["outcome"])
            tally[exp[2]] += 1
            if got != exp:
                mismatches.append({"instance": i, "kind": kind, "expected": exp, "got": got})
    # targeted: both nulls zero with LRU holding (the pre-fix false-positive path)
    lines = [f"instances {n} x 2 tree kinds; outcome distribution (auditor): {dict(tally)}",
             f"mismatches with arborlm.p7a_analysis.criteria: {len(mismatches)}"]
    for mm in mismatches[:20]:
        lines.append(f"  {mm}")
    (HERE / "outputs" / "conc_logic.txt").write_text("\n".join(lines) + "\n")
    (HERE / "outputs" / "conc_logic.json").write_text(json.dumps(
        {"instances": n, "tally": dict(tally), "mismatches": mismatches[:200]}, indent=1, default=str))
    print("\n".join(lines))
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
