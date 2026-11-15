"""Auditor's own implementation of ADR-0020 rev 4 sections 8.2-8.7 (cell success under both criteria, class per cell type, ADDRESS STABLE,
paired d, replication, cross-study consistency, preference order and candidate, outcome rows, hypothesis readings, OVERLOAD, WX label, probe label),
written from the ADR text only. It does NOT import studies.p10s0.classes or studies.p10s0.analysis. It is pure: inputs are plain dicts.

Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
"""

import math
from statistics import median

U = 8192
CORE = ("2K/4K", "8K/16K")
ORDER = ("A0", "A5-D", "A2", "A1")
LABEL_FREE = ("A0", "A5-D")
SUPERVISED = ("A1", "A2")


def fin_ge(x, b):
    return isinstance(x, float | int) and math.isfinite(x) and x >= b


def a6_usable(a6, ct):
    """A6 reference: (acc_a, acc_b, lm_rise) or None. Floor 0.50 at 8K/4K (section 8.2), else 0.90 (ADR-0019 condition 1)."""
    if a6 is None:
        return False
    floor = 0.50 if ct == "8K/4K" else 0.90
    return fin_ge(a6[0], floor) and fin_ge(a6[1], floor)


def verdict(o, a6, ct, s0):
    """o: dict of observation fields. Returns ('NE'|'S'|'F', lm_flag)."""
    if not a6_usable(a6, ct):
        return ("NE", False)
    ok = True
    # 1 accuracy >= 0.90 x A6 on both panels
    ok &= fin_ge(o["acc_a"], 0.90 * a6[0]) and fin_ge(o["acc_b"], 0.90 * a6[1])
    # 2 value permutation and memory-off inside the chance interval, both panels
    ok &= bool(o["dep_a"]) and bool(o["dep_b"])
    # 3 distinct >= 0.5 x probe facts and largest share <= 0.02
    ok &= o["probe_facts"] > 0 and o["distinct"] >= 0.5 * o["probe_facts"] and fin_ge(0.02 - o["share"], 0.0)
    # 4 H1 and H2 >= 0.90 x the cell's own accuracy, on both panels
    ok &= all(fin_ge(h, 0.90 * a) for h in (o["h1"], o["h2"]) for a in (o["acc_a"], o["acc_b"]))
    # 5 no leakage
    ok &= not o["leak"]
    # 6 (S0 only) a_use >= 0.95 x accuracy on Panels A and B
    if s0:
        ok &= fin_ge(o["ause_a"], 0.95 * o["acc_a"]) and fin_ge(o["ause_b"], 0.95 * o["acc_b"])
    rise, a6r = o["lm"], a6[2]
    flag = (not math.isfinite(rise)) or (math.isfinite(a6r) and rise > a6r + 0.05)
    return ("S" if ok else "F", flag)


def draw_status(vs_of_draw):
    if any(v == "NE" for v in vs_of_draw):
        return "NE"
    return "S" if all(v == "S" for v in vs_of_draw) else "F"


def arm_class(verdicts, rule):
    """verdicts: {(d, j): (status, flag)} for present cells. rule '20' or '10'. Section 8.3, first match wins."""
    draws = sorted({d for d, _ in verdicts})
    dstat = {d: draw_status([verdicts[k][0] for k in verdicts if k[0] == d]) for d in draws}
    ne_draws = sum(1 for s in dstat.values() if s == "NE")
    ev = {k: v for k, v in verdicts.items() if v[0] != "NE"}
    succ = sum(1 for v in ev.values() if v[0] == "S")
    fail = len(ev) - succ
    flagged = sum(1 for v in ev.values() if v[1])
    lm = flagged > 1
    both = any(sum(1 for k in ev if k[0] == d) >= 2 and all(ev[k][0] == "F" for k in ev if k[0] == d) for d in draws)
    if ne_draws > 1:
        cls = "NOT_EVALUATED"
    elif fail <= 1 and not both and not lm:
        cls = "RELIABLE"
    elif succ >= (5 if rule == "20" else 3):
        cls = "UNRELIABLE"
    else:
        cls = "FAILS"
    ok_d = sum(1 for s in dstat.values() if s == "S")
    f_d = sum(1 for s in dstat.values() if s == "F")
    return {"cls": cls, "succ": succ, "fail": fail, "lm": lm, "ne_draws": ne_draws, "draws_ok": ok_d, "draws_failed": f_d, "draws_ev": ok_d + f_d}


def stable(stabs_of_evaluated):
    """Median over the evaluated cells >= 0.80. Auditor's conservative reading: a non-finite cell value counts as 0.0 (it is kept in the
    denominator; nothing is dropped). statistics.median on NaN was the auditor's first, failed attempt (kept in failed_attempts/03)."""
    vals = [s if (isinstance(s, float | int) and math.isfinite(s)) else 0.0 for s in stabs_of_evaluated]
    if not vals:
        return False
    return median(vals) >= 0.80


def paired(x, a0):
    keys = [k for k in x if k in a0 and x[k][0] != "NE" and a0[k][0] != "NE"]
    xs = sum(1 for k in keys if x[k][0] == "S")
    a0s = sum(1 for k in keys if a0[k][0] == "S")
    b = sum(1 for k in keys if x[k][0] == "S" and a0[k][0] != "S")
    c = sum(1 for k in keys if a0[k][0] == "S" and x[k][0] != "S")
    d = b - c
    lab = "IMPROVES" if d >= 4 and xs > a0s else "HARMS" if d <= -4 else "ND"
    return lab, d


def replication(s0_p9crit_cls, p):
    if p is None or not p.get("available") or p["base_class"] == "NOT_EVALUATED" or s0_p9crit_cls == "NOT_EVALUATED":
        return "NOT COMPARABLE"
    return "REPLICATES" if (s0_p9crit_cls == "RELIABLE") == (p["base_class"] == "RELIABLE") else "DOES NOT REPLICATE"


def consistency(p, s0_failed_draws_p9crit, s0_eval_draws):
    if p is None or not p.get("available") or p["base_class"] == "NOT_EVALUATED":
        return ("SINGLE", True, None, None)
    pf = p["failed_draws"] + s0_failed_draws_p9crit
    pn = p["evaluated_draws"] + s0_eval_draws
    ok = (not p["lm_reduced"]) and pf <= 2
    return ("CONSISTENT" if ok else "INCONSISTENT", ok, pf, pn)


def select(evals):
    """evals[arm][ct] = {'meets', 'consistent'} for core cell types. Section 8.5 items 1-5."""
    q = {}
    for arm in ORDER:
        sizes = [ct for ct in CORE if evals[arm][ct]["meets"] and evals[arm][ct]["consistent"]]
        q[arm] = sizes
    cand = next((a for a in ORDER if tuple(q[a]) == CORE), None)
    q4096 = None if cand else next((a for a in ORDER if "2K/4K" in q[a]), None)
    first = cand or q4096
    also = []
    if first:
        for a in ORDER[ORDER.index(first) + 1 :]:
            if tuple(q[a]) == CORE:
                also.append((a, "BOTH"))
            elif "2K/4K" in q[a]:
                also.append((a, "4096"))
    return cand, q4096, also, q


def outcome(engineering, a6_2k4k_ne_draws, cand, q4096):
    if engineering:
        return 2
    if a6_2k4k_ne_draws > 1:
        return 3
    if cand:
        return 4
    if q4096:
        return 5
    return 6


def why_16384(e16):
    """Row 5 reason category: UNRELIABLE / FAILS / NOT_EVALUATED / not ADDRESS STABLE / INCONSISTENT."""
    c = e16["s0"]["cls"]
    if c == "NOT_EVALUATED":
        return "NOT_EVALUATED"
    if c != "RELIABLE":
        return c
    if not e16["stable"]:
        return "NOT STABLE"
    return "INCONSISTENT"


def overload(candidate, cls_8k4k):
    if candidate is None:
        return "NO CANDIDATE"
    if candidate in SUPERVISED:
        return "NOT RUN — NO TARGET INJECTION"
    if cls_8k4k is None:
        return "NOT_EVALUATED"
    return {"RELIABLE": "QUALIFIED", "NOT_EVALUATED": "NOT_EVALUATED"}.get(cls_8k4k, "NOT QUALIFIED")


def hypotheses(classes, paired_s0, repl, row, a0_fail_8k16k, ovl):
    out = {}
    a0 = classes["A0"]
    # H20-A (lead's ruling on m4, ADR-0020 addendum): supported if A0 is UNRELIABLE or FAILS at 2K/4K or at 8K/16K;
    # not supported if A0 is RELIABLE at both; not read otherwise  [re-check 2026-11-15: updated for the ruling]
    vals = [a0.get(ct) for ct in CORE]
    if any(v in ("UNRELIABLE", "FAILS") for v in vals):
        out["H20-A"] = "supported"
    elif all(v == "RELIABLE" for v in vals):
        out["H20-A"] = "not supported"
    else:
        out["H20-A"] = "not read"
    for h, arm in (("H20-B", "A1"), ("H20-C", "A2"), ("H20-D", "A5-D")):
        if all(classes[arm][ct] == "RELIABLE" and paired_s0[arm][ct][0] == "IMPROVES" for ct in CORE):
            r = "supported"
        elif any(paired_s0[arm][ct][0] == "HARMS" for ct in CORE):
            r = "CONTRADICTED"
        else:
            r = "not supported"
        out[h] = r
    for (arm, ct), lab in repl.items():
        out[f"H20-R ({arm}, {ct})"] = {"REPLICATES": "supported", "DOES NOT REPLICATE": "not supported"}.get(lab, "not read")
    out["H20-Q"] = "supported" if row == 4 else "not supported"
    # H20-O (lead's ruling, item 10): "not read" when OVERLOAD is NOT_EVALUATED; "not supported" when NOT QUALIFIED  [re-check: updated]
    out["H20-O"] = "supported" if ovl == "QUALIFIED" else ("not tested" if ovl in ("NOT RUN — NO TARGET INJECTION", "NO CANDIDATE") else "not read" if ovl == "NOT_EVALUATED" else "not supported")
    return out


def wx_label(wx_classes, wx_stable):
    """wx_classes[ct] class (10-cell rule), wx_stable[ct] bool."""
    if any(wx_classes[ct] == "NOT_EVALUATED" for ct in CORE):
        return "NOT_EVALUATED"
    ok = {ct: wx_classes[ct] == "RELIABLE" and wx_stable[ct] for ct in CORE}
    if all(ok.values()):
        return "PASSES"
    if ok["2K/4K"]:
        return "PASSES AT 4,096 ONLY"
    return "DOES NOT PASS"
