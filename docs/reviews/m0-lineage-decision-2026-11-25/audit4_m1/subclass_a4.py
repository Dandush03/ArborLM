# ruff: noqa
"""Audit 4 of M1: sizes of the subclasses on which the excluded 'procedure' rules and the new tells are right, per level. Seed 29 (audit throwaway), N per level.
Usage: PYTHONHASHSEED=0 PYTHONPATH=<impl> uv run --locked --offline python subclass_a4.py N"""
import math
import sys
from collections import Counter, defaultdict

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common_a4 import current_set, items
from studies.m0.lineages_m1_fix3_b import _RULES_FIRST, _RULES_LAST

SEED = 29


def pct(x):
    return f"{x:.3f}"


def main(N):
    cs = current_set(True)
    out = defaultdict(list)
    for lv in range(7):
        # slot_permutations
        its = items(cs["M1.slot_permutations_r3"], lv, N, SEED, "sub")
        anyc = hit_any = hit_not = nonany = noov_hit = norep = lz = 0
        for it in its:
            s = it.structured
            digs, ln, rep = s["digits"], s["length"], s["repeat"]
            nn = len(digs)
            npar = sum(1 for d in digs if _RULES_LAST[s["last"]](d))
            ign = npar * (nn ** (ln - 1) if rep else math.perm(nn - 1, ln - 1))
            ok = ign == int(it.answer)
            if s["first"] == "any":
                anyc += 1
                hit_any += ok
            else:
                nonany += 1
                hit_not += ok
            if not rep:
                norep += 1
                f = [d for d in digs if _RULES_FIRST[s["first"]](d)]
                p = [d for d in digs if _RULES_LAST[s["last"]](d)]
                noov_hit += len(f) * len(p) * math.perm(nn - 2, ln - 2) == int(it.answer)
            lz += 0 in digs and s["first"] in ("even", "lt5")
        out["slot: share of items with no first-digit rule ('any')"].append(pct(anyc / N))
        out["slot: ignore_first_rule right, within 'any' / within the rest"].append(f"{pct(hit_any / max(1, anyc))}/{pct(hit_not / max(1, nonany))}")
        out["slot: no-overlap-correction rule right (share of ALL items; no-repeat items only)"].append(pct(noov_hit / N))
        out["slot: leading-zero convention unstated and key-relevant (0 allowed, first rule even or < 5)"].append(pct(lz / N))
        # mode_tally 'others': predictability of n - f from n alone (exact conditional mode fitted on this sample: in-sample upper value) and n-5
        its = items(cs["M1.mode_tally_r3"], lv, N, SEED, "sub")
        oth = [it for it in its if it.structured["ask"] == "others"]
        by_n = defaultdict(Counter)
        for it in oth:
            by_n[len(it.structured["values"])][int(it.answer)] += 1
        best = sum(c.most_common(1)[0][1] for c in by_n.values()) / max(1, len(oth))
        # held-out version: fit on even, score on odd
        tr, te = oth[0::2], oth[1::2]
        bt = defaultdict(Counter)
        for it in tr:
            bt[len(it.structured["values"])][int(it.answer)] += 1
        ho = sum(1 for it in te if bt[len(it.structured["values"])] and bt[len(it.structured["values"])].most_common(1)[0][0] == int(it.answer)) / max(1, len(te))
        out["mode_tally 'others': key = the most frequent key for the printed list length n (in-sample / held-out), within the ask"].append(f"{pct(best)}/{pct(ho)}")
        out["mode_tally: share of 'others' asks"].append(pct(len(oth) / N))
        # pigeonhole
        its = items(cs["M1.pigeonhole_worst_case_r3"], lv, N, SEED, "sub")
        same = [it for it in its if it.structured["goal"] == "same"]
        sub = sum(1 for it in same if all(c <= it.structured["k"] - 1 for c in sorted(it.structured["counts"])[:-1]))
        caps_idle = sum(1 for it in same if all(c >= it.structured["k"] - 1 for c in it.structured["counts"]))
        out["pigeonhole 'same': every colour but the largest has <= k-1 marbles (rule 'others, then k' exact)"].append(pct(sub / max(1, len(same))))
        out["pigeonhole 'same': every colour has >= k-1 marbles (rule 'ignore caps' exact)"].append(pct(caps_idle / max(1, len(same))))
        # coins
        its = items(cs["M1.coins_r3"], lv, N, SEED, "sub")
        hi = [it for it in its if it.structured["ask"] == "hi"]
        lo = [it for it in its if it.structured["ask"] == "lo"]
        r_hi = sum(1 for it in hi if it.structured["cents"] // it.structured["hi"] - 1 == int(it.answer)) / max(1, len(hi))
        r_hi0 = sum(1 for it in hi if it.structured["cents"] // it.structured["hi"] == int(it.answer)) / max(1, len(hi))
        r_lo = sum(1 for it in lo if it.structured["count"] - (it.structured["cents"] // it.structured["hi"] - 1) == int(it.answer)) / max(1, len(lo))
        out["coins 'hi' ask: floor(total/hi) right / floor(total/hi) - 1 right"].append(f"{pct(r_hi0)}/{pct(r_hi)}")
        out["coins 'lo' ask: count - (floor(total/hi) - 1) right"].append(pct(r_lo))
        # last_digit_power: exponent <= modulus (no reduction to do) on every term
        its = items(cs["M1.last_digit_power_r3"], lv, N, SEED, "sub")
        out["power: every exponent <= p (Fermat reduction idle)"].append(pct(sum(1 for it in its if all(e <= it.structured["modulus"] for _, e in it.structured["terms"])) / N))
        # division: exact fit
        its = items(cs["M1.division_counting_r3"], lv, N, SEED, "sub")
        seats = [it for it in its if it.structured["shape"] == "empty_seats"]
        out["division 'empty seats': exact fit (k - N mod k wrong)"].append(pct(sum(1 for it in seats if it.structured["people"] % it.structured["seats"] == 0) / max(1, len(seats))))
        # speed_distance average: answer equals a printed speed
        its = items(cs["M1.speed_distance_r3"], lv, N, SEED, "sub")
        av = [it for it in its if it.structured["average"]]
        out["speed average ask: key equals one of the printed speeds"].append(pct(sum(1 for it in av if int(it.answer) in [v for _, v in it.structured["legs"]]) / max(1, len(av))) if av else "-")
        # gcd_lcm: k >= 3 share
        its = items(cs["M1.gcd_lcm_r3"], lv, N, SEED, "sub")
        out["gcd_lcm: items with k >= 3 (false rule product/gcd^(k-1) or product/lcm^(k-1) exact)"].append(pct(sum(1 for it in its if len(it.structured["values"]) >= 3) / N))
    for k, v in out.items():
        print(f"{k}: {' '.join(v)}")


if __name__ == "__main__":
    main(int(sys.argv[1]))
