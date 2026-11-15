"""Auditor C's own implementation of ADR-0022 rev 5 sections 10.1 and 11 (gap closed, ACQ1/ACQ2/RET/GEN,
mechanism classes, label rows), written from the ADR text only. Readings fixed by the lead (freeze README
1-5) are applied where the ADR is silent; every other choice is marked AUDITOR-READING.

Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
"""

import math

UNDEF = "UNDEF"
GAP_MIN = 0.30


def fin(*xs):
    return all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in xs)


def gap(arm, s0, t):
    """section 10.1: G = (arm - s0)/(t - s0), defined only if t - s0 >= 0.30; else NOT_EVALUATED."""
    if not fin(arm, s0, t):
        return UNDEF
    d = t - s0
    if d < GAP_MIN:
        return UNDEF
    return (arm - s0) / d


class Cell:
    """Abstract per-cell raw numbers. panels: {'E_A': x, 'E_B': y}; abl: {panel: {'unablated','value_perm','code_perm','marker_only'}}"""

    def __init__(self, status="completed", panels=None, abl=None, gen=None, rejected=False, below_floor=False):
        self.status = status
        self.panels = panels or {}
        self.abl = abl  # None means: section absent
        self.gen = gen
        self.rejected = rejected
        self.below_floor = below_floor


def G_full(base, cell, panel):
    if cell is None or cell.status != "completed" or panel not in cell.panels:
        return UNDEF
    return gap(cell.panels[panel], base["s0"][panel], base["t"][panel])


def G_sub(base, x, panel):
    return gap(x, base["s0sub"][panel], base["tsub"][panel])


def lexical(base, cell, panel):
    """(margin_ok, marker_ok) or UNDEF. Lead reading 2: on the 300-item subsample."""
    if cell.abl is None or panel not in cell.abl:
        return UNDEF  # AUDITOR-READING: a memory cell with no ablation record cannot pass the control clauses
    a = cell.abl[panel]
    gs = [G_sub(base, a.get(k), panel) for k in ("unablated", "value_perm", "code_perm", "marker_only")]
    if any(g == UNDEF for g in gs):
        return UNDEF
    u, vp, cp, mo = gs
    return (u - max(vp, cp) >= 0.30, mo <= 0.25)


def acq(G, lex, g_single=None, ratio=False):
    """Returns (verdict, undefined_flag). verdict True/False on defined parts; undefined_flag if any input gap undefined."""
    und = G == UNDEF or (ratio and g_single == UNDEF) or lex == UNDEF
    fails = []
    if G != UNDEF and G < 0.50:
        fails.append("acq")
    if ratio and G != UNDEF and g_single != UNDEF and G < 0.80 * g_single:
        fails.append("ratio")
    if lex not in (None, UNDEF):
        if not lex[0]:
            fails.append("margin")
        if not lex[1]:
            fails.append("marker")
    return (not fails and not und), und, fails


MECH = {"M-append-frozen": ("MAF", "ST1"), "M-ii": ("MII", "ST1"), "M-seq": ("MSEQ", "ST1"), "L-seq": ("LSEQ", "LORA1")}


def flip(o):
    return o[::-1]


def rep_eval(base, cells, r, mech, o):
    g, fg = MECH[mech]
    f, s = o[0], o[1]
    pf, ps = "E_" + f, "E_" + s
    v1 = cells.get((r, fg, o))
    me = cells.get((r, g, o))
    single = cells.get((r, fg, flip(o)))
    lora = fg == "LORA1"
    G_v1 = G_full(base, v1, pf)
    a1_ok, a1_und, _ = acq(G_v1, None if lora else lexical(base, v1, pf))
    G2 = G_full(base, me, ps)
    G_single = G_full(base, single, ps)
    a2_ok, a2_und, a2_f = acq(G2, None if lora else lexical(base, me, ps), G_single, ratio=True)
    s_after = me.panels.get(pf) if me else None
    s_v1 = v1.panels.get(pf) if v1 else None
    G_after = G_full(base, me, pf)
    r_und = not fin(s_after, s_v1) or G_after == UNDEF or G_v1 == UNDEF
    r_ok = (not r_und) and s_after >= s_v1 - 0.03 and G_after >= 0.90 * G_v1
    neg_acq = None if G2 == UNDEF else G2 < 0.25
    neg_ret = None if (G_after == UNDEF or G_v1 == UNDEF) else G_after < 0.70 * G_v1
    return dict(a1_ok=a1_ok, a1_und=a1_und, a2_ok=a2_ok, a2_und=a2_und, a2_f=a2_f, r_ok=r_ok, r_und=r_und, neg_acq=neg_acq, neg_ret=neg_ret,
                rejected=bool(me.rejected) if me else False, below_floor=bool(me.below_floor) if me else False)


def mech_class(base, cells, n, mech, o, *, strict_undefined=True):
    """section 11.2, first match wins. strict_undefined: row 1 'a gap is undefined' applies to any gap the gates use
    (AUDITOR-READING of the ADR text: an undefined gap gives NOT_EVALUATED even if another clause fails)."""
    g, fg = MECH[mech]
    need = [(r, g, o) for r in range(n)] + [(r, fg, o) for r in range(n)] + [(r, fg, flip(o)) for r in range(n)]
    if mech == "M-ii":
        need += [(r, "MAF", o) for r in range(n)]  # M-ii continues M-append-frozen (registry dependency)
    if any(cells.get(k) is None or cells[k].status != "completed" for k in need):
        return "NO CLASS (INCOMPLETE)"
    ev = [rep_eval(base, cells, r, mech, o) for r in range(n)]
    for e in ev:
        if not e["a1_ok"]:
            return "NOT_EVALUATED"
        if strict_undefined and (e["a2_und"] or e["r_und"]):
            return "NOT_EVALUATED"
        if not strict_undefined and ((e["a2_und"] and not e["a2_f"]) or e["r_und"]):
            return "NOT_EVALUATED"
    if all(e["neg_acq"] for e in ev):
        return "NO-NEW-CAPABILITY"
    if all(e["neg_ret"] for e in ev):
        return "FORGETS"
    passes = [e["a2_ok"] and e["r_ok"] for e in ev]
    if mech == "M-ii" and all(passes) and any(e["below_floor"] for e in ev):
        return "RETENTION BY INERTIA"
    if all(passes) and not (mech == "M-ii" and any(e["rejected"] for e in ev)):
        return "ACQUIRES-AND-RETAINS"
    if any(passes) and any((e["neg_acq"] or e["neg_ret"]) for e in ev):
        return "NOT REPLICATED"
    return "INTERMEDIATE"


REGISTRY_GROUPS = [("ST1", ("AB", "BA")), ("MAF", ("AB", "BA")), ("MII", ("AB", "BA")), ("MSEQ", ("AB", "BA")), ("LORA1", ("AB", "BA")), ("LSEQ", ("AB", "BA")),
                   ("ETABLE", ("A", "B")), ("MAGOLD", ("A", "B")), ("MJOINT", ("-",)), ("LJOINT", ("-",))]


def gen_ok(cells, n, group, o):
    """Lead reading 4: GEN holds for an arm in an order iff it holds at its first-stage (ST1) and stage-2 snapshot in every replicate; missing/non-finite = not a hold."""
    for r in range(n):
        for gg in ("ST1", group):
            c = cells.get((r, gg, o))
            v = None if c is None or c.status != "completed" else c.gen
            if not fin(v) or not v <= 0.02:
                return False
    return True


def control_failed(base, cells, n):
    """Label row 5 with lead reading 3 (panel = the capability the permutation targets)."""
    tgt = {"ST1": lambda v: ["E_" + v[0]], "MAGOLD": lambda v: ["E_" + v], "MAF": lambda v: ["E_" + v[1]], "MII": lambda v: ["E_" + v[1]],
           "MSEQ": lambda v: ["E_A", "E_B"], "MJOINT": lambda v: ["E_A", "E_B"]}
    for (r, g, v), c in cells.items():
        if g not in tgt or c.status != "completed" or c.abl is None:
            continue
        for p in tgt[g](v):
            if p not in c.abl:
                continue
            for k in ("value_perm", "code_perm"):
                gv = G_sub(base, c.abl[p].get(k), p)
                if gv != UNDEF and gv >= 0.50:
                    return True
    return False


def label(base, cells, n, *, gates_ok=True, engineering=False, prefreeze_stop=None, teacher_only=True, strict_undefined=True):
    if engineering or not gates_ok:
        return 1
    for r in range(n):
        for g, vs in REGISTRY_GROUPS:
            for v in vs:
                c = cells.get((r, g, v))
                if c is None or c.status != "completed":
                    return 2
    if prefreeze_stop:
        return 3
    neg = []
    for r in range(n):
        for o in ("AB", "BA"):
            G = G_full(base, cells[(r, "ST1", o)], "E_" + o[0])
            neg.append(G != UNDEF and G < 0.25)
    if all(neg):
        return 4
    if control_failed(base, cells, n):
        return 5
    cls = {m: {o: mech_class(base, cells, n, m, o, strict_undefined=strict_undefined) for o in ("AB", "BA")} for m in MECH}
    AR = "ACQUIRES-AND-RETAINS"
    maf_ar = all(cls["M-append-frozen"][o] == AR for o in ("AB", "BA"))
    mii_ar = all(cls["M-ii"][o] == AR for o in ("AB", "BA"))
    gmaf = all(gen_ok(cells, n, "MAF", o) for o in ("AB", "BA"))
    gmii = all(gen_ok(cells, n, "MII", o) for o in ("AB", "BA"))
    if maf_ar and teacher_only and not gmaf:
        return 6
    if maf_ar and mii_ar and teacher_only and gmaf and gmii:
        return 7
    if maf_ar and teacher_only and gmaf:
        return 8
    if all(cls["M-append-frozen"][o] == "FORGETS" for o in ("AB", "BA")):
        return 9
    if all(cls["M-append-frozen"][o] == "NO-NEW-CAPABILITY" for o in ("AB", "BA")):
        return 10
    if sum(cls["M-append-frozen"][o] == AR for o in ("AB", "BA")) == 1:
        return 11
    return 12


# --- chrF from the definition of section 10.1 (independent of studies/p10s2/text.py) ---------------------------
import unicodedata


def norm(t):
    t = unicodedata.normalize("NFC", t).lower()
    t = "".join(ch for ch in t if not unicodedata.category(ch).startswith("P"))
    return " ".join(t.split())


def chrf_def(hyp, ref, N=6, beta=2.0):
    h = norm(hyp).replace(" ", "")
    r = norm(ref).replace(" ", "")
    P, R, k = [], [], 0
    for n in range(1, N + 1):
        hc, rc = {}, {}
        for i in range(len(h) - n + 1):
            hc[h[i:i + n]] = hc.get(h[i:i + n], 0) + 1
        for i in range(len(r) - n + 1):
            rc[r[i:i + n]] = rc.get(r[i:i + n], 0) + 1
        th, tr = sum(hc.values()), sum(rc.values())
        if th == 0 or tr == 0:
            continue
        m = sum(min(c, rc.get(g, 0)) for g, c in hc.items())
        P.append(m / th)
        R.append(m / tr)
        k += 1
    if k == 0:
        return 0.0
    p, rr = sum(P) / k, sum(R) / k
    if p + rr == 0:
        return 0.0
    b2 = beta * beta
    return (1 + b2) * p * rr / (b2 * p + rr)
