"""Independent enumeration of ADR-0020 §3 (mapping from P9-II's registered outcome to S0's arms).

Written by the auditor from the text of ADR-0019 rev4 §5, §8.4, §8.6 and ADR-0020 §3.2-§3.4 only.
No project code is imported.

Model of P9-II's registered record (inputs listed in ADR-0020 §3.1):
  cls4[X]  class at 4,096 (Stage 1) for X in A0, A5-C, A5-D, A4, A2, A1:
           R (RELIABLE), U (UNRELIABLE), ULM (UNRELIABLE (LM CAPABILITY REDUCED)), F (FAILS),
           FLM (FAILS with LM CAPABILITY REDUCED printed). Stage-1 NOT_EVALUATED is draw-level and
           makes every arm NE; it is enumerated as one extra case.
  NC4, NC16  NEGATIVE CONTROL FAILED printed at 4,096 / 16,384.
  Stage 1 gate (ADR-0019 §8.4): Stage 2 runs if some arm is eligible (RELIABLE at 4,096, and for
           A1/A2 not NC4); A0 always runs at Stage 2 when it runs; besides A0 at most two arms, in
           the order A5-C, A5-D, A4, A2, A1.
  st2      Stage 2 status: COMPLETE, BUDGET, INCOMPLETE, NE (stage-level) or NORUN (no arm passed).
  cls16[X] for advanced X when st2 == COMPLETE: R, U, ULM, F, FLM, NE.
  For st2 == INCOMPLETE we also test a 'loose' record in which some advanced arms still print a
  class (the case that makes ADR-0020's c16 definition overlap).

Outputs: counts per P9-II outcome row; disagreement between §3.3 (rule) and §3.4 (table, literal
reading); reachable branches that the table does not list; the c16 ambiguity; the 'E and E4 empty
under rows 3-6' branch and its label.

Usage: python3 -I c2_mapping_enumeration.py
"""

import itertools
from collections import Counter, defaultdict

ARMS = ["A0", "A5-C", "A5-D", "A4", "A2", "A1"]          # carry-forward / rank order
GATE_ORDER = ["A5-C", "A5-D", "A4", "A2", "A1"]            # ADR-0019 Stage 1 gate order
SUP = {"A1", "A2"}
LABEL_FREE = {"A0", "A4", "A5-C", "A5-D"}
CLS4 = ["R", "U", "ULM", "F", "FLM"]
CLS16 = ["R", "U", "ULM", "F", "FLM", "NE"]


def lm(c):
    return c in ("ULM", "FLM")


# ---------------------------------------------------------------- P9-II (ADR-0019 rev4 §8.4, §8.6)
def p9ii_advanced(cls4, nc4):
    elig = [x for x in GATE_ORDER if cls4[x] == "R" and not (x in SUP and nc4)]
    a0_elig = cls4["A0"] == "R"
    runs = bool(elig) or a0_elig
    return runs, (["A0"] + elig[:2]) if runs else []


def p9ii_outcome(stage1_ne, cls4, nc4, nc16, st2, cls16):
    if stage1_ne:
        return "INCONCLUSIVE"
    label_free_r4 = any(cls4[x] == "R" for x in LABEL_FREE)
    if nc4 and not label_free_r4:
        return "INCONCLUSIVE"
    if cls4["A0"] == "R":
        return "ANSWER-ONLY RELIABLE"

    def skipped(x, size):
        return x in SUP and (nc4 if size == 4 else (nc4 or nc16))

    r4 = [x for x in ARMS if x != "A0" and cls4[x] == "R" and not skipped(x, 4)]
    if r4:
        if st2 == "COMPLETE":
            r16 = [x for x in r4 if cls16.get(x) == "R" and not skipped(x, 16)]
            return "ADDRESSING-RELIABLE" if r16 else "ADDRESSING-RELIABLE AT 4,096 ONLY"
        return "ADDRESSING-RELIABLE AT 4,096; 16,384 <status>"
    others = [cls4[x] for x in ARMS]
    if any(c in ("U", "ULM") for c in others):
        return "ADDRESSING-UNRELIABLE"
    if all(c in ("F", "FLM") for c in others):
        return "ADDRESSING-FAILS"
    return "UNCLASSIFIED"  # would be a P9-II gap


def p9ii_carried(cls4, nc4, nc16, st2, cls16):
    """First RELIABLE arm at 16,384 in the order A0, A5-C, A5-D, A4, A2, A1, not LM-flagged, not
    NC-skipped (ADR-0019 §8.6 last bullet)."""
    if st2 != "COMPLETE":
        return None
    for x in ARMS:
        if cls16.get(x) == "R" and not (x in SUP and (nc4 or nc16)):
            return x
    return None


# ---------------------------------------------------------------- S0 rule (ADR-0020 §3.2, §3.3)
def s0_rule(cls4, nc4, nc16, st2, cls16, advanced, c16_reading="strict"):
    def excluded(x):
        return lm(cls4[x]) or lm(cls16.get(x, "")) or (x in SUP and (nc4 or nc16))

    def c16(x):
        if c16_reading == "strict":
            if st2 != "COMPLETE" or x not in advanced or cls16.get(x) in (None, "NE"):
                return "UNTESTED"
            return "RELIABLE" if cls16[x] == "R" else "FAILED"
        # 'loose' reading: RELIABLE is read first, whatever the stage status (definition order)
        if cls16.get(x) == "R":
            return "RELIABLE"
        if st2 == "COMPLETE" and x in advanced and cls16.get(x) not in (None, "NE"):
            return "FAILED"
        return "UNTESTED"

    pool = [x for x in ARMS if not excluded(x) and cls4[x] == "R"]
    E = [x for x in pool if c16(x) != "FAILED"]
    E4 = [x for x in pool if c16(x) == "FAILED"]
    E.sort(key=lambda x: (0 if c16(x) == "RELIABLE" else 1, ARMS.index(x)))
    E4.sort(key=ARMS.index)
    if E:
        src, scope = E, "FULL"
    elif E4:
        src, scope = E4, "SMALL"
    else:
        return None, None, None, E, E4, {x: c16(x) for x in ARMS}
    c = src[0]
    rest = [x for x in src if x != c]
    cls = (lambda x: "SUP" if x in SUP else "LF")
    diff = [x for x in rest if cls(x) != cls(c)]
    x2 = diff[0] if diff else (rest[0] if rest else None)
    return c, x2, scope, E, E4, {x: c16(x) for x in ARMS}


# ---------------------------------------------------------------- S0 table (§3.4), literal reading
def s0_table(outcome, carried, cls4, st2, E, E4, c16):
    """Returns (C, X2, scope) or a string for rows 7-10 / 'UNLISTED' if no row covers the case."""
    if outcome in ("ADDRESSING-UNRELIABLE", "ADDRESSING-FAILS"):
        return "NO RUN (rows 7-8)"
    if outcome == "INCONCLUSIVE":
        return "NO RUN (row 9)"
    if not E and not E4:
        return "NO RUN (row 9 via exclusions)"
    if outcome == "ADDRESSING-RELIABLE":
        if carried in ("A5-C", "A5-D", "A4"):
            c = carried
            sup = [x for x in E if x in SUP]
            lf = [x for x in E if x not in SUP and x != c]
            return (c, sup[0] if sup else (lf[0] if lf else None), "FULL")
        if carried in ("A2", "A1"):
            c = "A2" if c16.get("A2") == "RELIABLE" and "A2" in E else "A1"
            lf = [x for x in E if x in LABEL_FREE]
            other = [x for x in E if x in SUP and x != c]
            return (c, lf[0] if lf else (other[0] if other else None), "FULL")
        return "UNLISTED (row 1/2: carried arm is %s)" % carried
    if outcome == "ANSWER-ONLY RELIABLE":
        a0c = c16.get("A0")
        if "A0" in E and a0c == "RELIABLE":
            sup = [x for x in E if x in SUP]
            oth = [x for x in E if x != "A0"]
            return ("A0", sup[0] if sup else (oth[0] if oth else None), "FULL")
        if "A0" not in E and "A0" not in E4:
            return "UNLISTED (row 3/4: A0 excluded)"
        if a0c == "UNTESTED":
            tier1 = [x for x in E if c16[x] == "RELIABLE"]
            c = tier1[0] if tier1 else "A0"
        else:  # FAILED
            c = E[0] if E else "A0"
        src = E if c in E else E4
        rest = [x for x in src if x != c]
        cls = (lambda x: "SUP" if x in SUP else "LF")
        diff = [x for x in rest if cls(x) != cls(c)]
        return (c, diff[0] if diff else (rest[0] if rest else None), "FULL" if c in E else "SMALL")
    if outcome == "ADDRESSING-RELIABLE AT 4,096 ONLY":
        untested = [x for x in E if c16[x] == "UNTESTED"]
        if untested:
            return (untested[0], "by rule", "FULL")
        return (E4[0], "by rule", "SMALL")
    if outcome == "ADDRESSING-RELIABLE AT 4,096; 16,384 <status>":
        return (E[0] if E else None, "by rule", "FULL")
    return "UNLISTED (%s)" % outcome


def main():
    rows = Counter()
    s0_branch = Counter()
    disagreements = defaultdict(list)
    unlisted = defaultdict(list)
    empty_by_exclusion = defaultdict(list)
    c16_ambig = []
    small_scope = Counter()
    unclassified = 0
    n = 0
    for combo in itertools.product(CLS4, repeat=len(ARMS)):
        cls4 = dict(zip(ARMS, combo))
        for nc4 in (False, True):
            runs, adv = p9ii_advanced(cls4, nc4)
            st2_opts = ["COMPLETE", "BUDGET", "INCOMPLETE", "NE"] if runs else ["NORUN"]
            sup_adv = any(x in SUP for x in adv)
            for st2 in st2_opts:
                # NC16 can be printed only if Stage 2 ran (fix of attempt 1, which allowed it always)
                for nc16 in ((False, True) if sup_adv and st2 in ("COMPLETE", "INCOMPLETE") else (False,)):
                    if st2 == "COMPLETE":
                        cls16_iter = (dict(zip(adv, v)) for v in itertools.product(CLS16, repeat=len(adv)))
                    elif st2 == "INCOMPLETE":
                        # strict: no class printed; loose: some advanced arms printed R
                        cls16_iter = iter([{}] + [{x: "R"} for x in adv])
                    else:
                        cls16_iter = iter([{}])
                    for cls16 in cls16_iter:
                        n += 1
                        out = p9ii_outcome(False, cls4, nc4, nc16, st2 if st2 != "NORUN" else "NORUN", cls16)
                        if out == "UNCLASSIFIED":
                            unclassified += 1
                            continue
                        rows[out] += 1
                        carried = p9ii_carried(cls4, nc4, nc16, st2, cls16)
                        c, x2, scope, E, E4, c16 = s0_rule(cls4, nc4, nc16, st2, cls16, adv, "strict")
                        if st2 == "INCOMPLETE" and cls16:
                            c_l, x2_l, scope_l, *_ = s0_rule(cls4, nc4, nc16, st2, cls16, adv, "loose")
                            if (c, x2, scope) != (c_l, x2_l, scope_l) and len(c16_ambig) < 6:
                                c16_ambig.append((combo, nc4, st2, cls16, (c, x2, scope), (c_l, x2_l, scope_l)))
                            elif (c, x2, scope) != (c_l, x2_l, scope_l):
                                c16_ambig.append(None)
                        no_run_rows = out in ("ADDRESSING-UNRELIABLE", "ADDRESSING-FAILS", "INCONCLUSIVE")
                        if no_run_rows:
                            assert c is None, (combo, out, c)  # E and E4 must be empty in rows 7-9
                            s0_branch["no run: " + out] += 1
                            continue
                        if c is None:
                            s0_branch["no run: E,E4 empty under " + out] += 1
                            if len(empty_by_exclusion[out]) < 2:
                                empty_by_exclusion[out].append((combo, nc4, nc16, st2, cls16))
                            continue
                        s0_branch[f"run {scope}"] += 1
                        if scope == "SMALL":
                            small_scope[(out, c)] += 1
                        tab = s0_table(out, carried, cls4, st2, E, E4, c16)
                        if isinstance(tab, str):
                            if len(unlisted[tab]) < 2:
                                unlisted[tab].append((combo, nc4, nc16, st2, cls16, (c, x2, scope)))
                            else:
                                unlisted[tab].append(None)
                            continue
                        tc, tx2, tscope = tab
                        if tc != c or tscope != scope or (tx2 != "by rule" and tx2 != x2):
                            key = f"{out} | rule C={c} X2={x2} {scope} | table C={tc} X2={tx2} {tscope}"
                            disagreements[key].append((combo, nc4, nc16, st2, cls16))
    print(f"enumerated records: {n}; P9-II UNCLASSIFIED (gap in ADR-0019 §8.6): {unclassified}")
    print("\nP9-II outcome rows (count of enumerated records):")
    for k, v in sorted(rows.items()):
        print(f"  {v:>9}  {k}")
    print("\nS0 branch:")
    for k, v in sorted(s0_branch.items()):
        print(f"  {v:>9}  {k}")
    print("\nSMALL-scope candidates by P9-II outcome:")
    for k, v in sorted(small_scope.items()):
        print(f"  {v:>9}  {k}")
    print("\nE and E4 both empty under P9-II rows 3-6 (ADR-0020 prints 'INCONCLUSIVE (P9-II INCONCLUSIVE; S0 NOT RUN)'):")
    for k, v in empty_by_exclusion.items():
        for ex in v:
            print(f"  {k}: cls4={dict(zip(ARMS, ex[0]))} NC4={ex[1]} NC16={ex[2]} st2={ex[3]} cls16={ex[4]}")
    print("\nCases the §3.4 table does not list (rule still decides):")
    for k, v in unlisted.items():
        print(f"  {len(v):>9}  {k}")
        ex = v[0]
        print(f"             e.g. cls4={dict(zip(ARMS, ex[0]))} NC4={ex[1]} NC16={ex[2]} st2={ex[3]} cls16={ex[4]} -> rule {ex[5]}")
    print("\nRule vs table disagreements (literal reading of the table):")
    if not disagreements:
        print("  none")
    for k, v in sorted(disagreements.items(), key=lambda kv: -len(kv[1]))[:25]:
        ex = v[0]
        print(f"  {len(v):>9}  {k}")
        print(f"             e.g. cls4={dict(zip(ARMS, ex[0]))} NC4={ex[1]} NC16={ex[2]} st2={ex[3]} cls16={ex[4]}")
    amb = [a for a in c16_ambig if a]
    print(f"\nc16 ambiguity (Stage 2 INCOMPLETE but an arm's 16,384 class printed RELIABLE): "
          f"{len(c16_ambig)} records where strict and loose readings choose different arms/scope")
    for a in amb[:4]:
        print(f"  cls4={dict(zip(ARMS, a[0]))} NC4={a[1]} st2={a[2]} cls16={a[3]} strict={a[4]} loose={a[5]}")


if __name__ == "__main__":
    main()
