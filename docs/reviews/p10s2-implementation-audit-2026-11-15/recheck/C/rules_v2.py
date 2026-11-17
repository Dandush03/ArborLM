"""Re-check auditor C: my own implementation of ADR-0022 sections 10.1 and 11 (classes and label rows) UPDATED for the
lead's rulings (ADR-0022 addenda of 2026-11-15) and of the combined-tasks addendum section 8 (COMPOSES).
Written from the ADR text; it does not import studies.p10s2. Based on the predecessor's spec_rules.py (auditor code).

Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.

Rulings applied (ADR-0022, "rulings on the three implementation audits" and "points the fix lanes left open"):
 R1 missing gates record / missing gate (G1..G9, G2 and G3 included) / missing ensemble record -> INCOMPLETE (row 2)
 R2 a present gate that failed (G1, G2, G4..G9) -> ENGINEERING-FAILURE (row 1); ensemble score != teacher's own -> row 1
 R3 a missing control (ablation section, panel or kind) of a memory cell -> NOT_EVALUATED for its ACQ clause;
    a permutation control that is NOT_EVALUATED in ANY cell blocks rows 6-8
 R4 undefined gap -> NOT_EVALUATED first (C-M4)
 R5 GEN for an arm/order holds only if, for ST1/o and the arm's stage-2 snapshot in every replicate, BOTH loss increases
    (token-64 and first-marker decision) are finite and <= 0.02; a measured value > 0.02 under either decision is a
    failure; a missing/non-finite value with no failure is NOT_EVALUATED: rows 6-8 do not apply (reading 4 corrected)
 R6 a missing combined record of a scored arm is a missing registered score -> INCOMPLETE
    (AUDITOR-READING: except for a CONSOLIDATION-REJECTED M-ii cell, which the addendum s7 says has no combined score)
"""

import math

UNDEF = "UNDEF"
GAP_MIN = 0.30
ORDERS = ("AB", "BA")
TASKS = ("A", "B")


def fin(*xs):
    return all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in xs)


def gap(arm, s0, t):
    if not fin(arm, s0, t):
        return UNDEF
    d = t - s0
    if d < GAP_MIN:
        return UNDEF
    return (arm - s0) / d


class Cell:
    def __init__(self, status="completed", panels=None, abl=None, gen=None, rejected=False, below_floor=False):
        self.status = status
        self.panels = panels or {}
        self.abl = abl  # None: section absent; {panel: {kind: score}}; a kind may be absent
        self.gen = gen  # None (no gen record) or (inc64, inc_first_marker), each a float/'nan'/None
        self.rejected = rejected
        self.below_floor = below_floor


def G_full(base, cell, panel):
    if cell is None or cell.status != "completed" or panel not in cell.panels:
        return UNDEF
    return gap(cell.panels[panel], base["s0"][panel], base["t"][panel])


def G_sub(base, x, panel):
    return gap(x, base["s0sub"][panel], base["tsub"][panel])


def lexical(base, cell, panel):
    if cell.abl is None or panel not in cell.abl:
        return UNDEF
    a = cell.abl[panel]
    if any(k not in a for k in ("unablated", "value_perm", "code_perm", "marker_only")):
        return UNDEF
    gs = [G_sub(base, a[k], panel) for k in ("unablated", "value_perm", "code_perm", "marker_only")]
    if any(g == UNDEF for g in gs):
        return UNDEF
    u, vp, cp, mo = gs
    return (u - max(vp, cp) >= 0.30, mo <= 0.25)


def acq(G, lex, g_single=None, ratio=False):
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
    v1, me, single = cells.get((r, fg, o)), cells.get((r, g, o)), cells.get((r, fg, flip(o)))
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
    return dict(a1_ok=a1_ok, a2_ok=a2_ok, a2_und=a2_und, r_ok=r_ok, r_und=r_und, neg_acq=neg_acq, neg_ret=neg_ret,
                rejected=bool(me.rejected) if me else False, below_floor=bool(me.below_floor) if me else False)


def mech_class(base, cells, n, mech, o):
    g, fg = MECH[mech]
    need = [(r, g, o) for r in range(n)] + [(r, fg, o) for r in range(n)] + [(r, fg, flip(o)) for r in range(n)]
    if any(cells.get(k) is None or cells[k].status != "completed" for k in need):
        return "NO CLASS (INCOMPLETE)"
    ev = [rep_eval(base, cells, r, mech, o) for r in range(n)]
    for e in ev:
        if not e["a1_ok"] or e["a2_und"] or e["r_und"]:
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


REGISTRY_GROUPS = [("ST1", ORDERS), ("MAF", ORDERS), ("MII", ORDERS), ("MSEQ", ORDERS), ("LORA1", ORDERS), ("LSEQ", ORDERS),
                   ("ETABLE", TASKS), ("MAGOLD", TASKS), ("MJOINT", ("-",)), ("LJOINT", ("-",))]


def gen_status(cells, n, group, o):
    """'fails' | 'not_evaluated' | 'holds' (R5)."""
    vals = []
    for r in range(n):
        for gg in ("ST1", group):
            c = cells.get((r, gg, o))
            if c is None or c.status != "completed" or c.gen is None:
                vals += [None, None]
            else:
                vals += list(c.gen)
    if any(fin(v) and v > 0.02 for v in vals):
        return "fails"
    if all(fin(v) for v in vals):
        return "holds"
    return "not_evaluated"


TARGET = {"ST1": lambda v: ["E_" + v[0]], "MAGOLD": lambda v: ["E_" + v], "MAF": lambda v: ["E_" + v[1]], "MII": lambda v: ["E_" + v[1]],
          "MSEQ": lambda v: ["E_A", "E_B"], "MJOINT": lambda v: ["E_A", "E_B"]}


def controls(base, cells):
    """(any_failed, any_not_evaluated) over value/code permutation controls of every completed memory cell (reading 3 panels)."""
    failed = ne = False
    for (r, g, v), c in cells.items():
        if g not in TARGET or c.status != "completed":
            continue
        for p in TARGET[g](v):
            for k in ("value_perm", "code_perm"):
                if c.abl is None or p not in c.abl or k not in c.abl[p]:
                    ne = True
                    continue
                gv = G_sub(base, c.abl[p][k], p)
                if gv == UNDEF:
                    ne = True
                elif gv >= 0.50:
                    failed = True
    return failed, ne


REQUIRED_GATES = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9")
ENG_GATES = ("G1", "G2", "G4", "G5", "G6", "G7", "G8", "G9")
COMP = {"MAF": ORDERS, "MII": ORDERS, "LSEQ": ORDERS, "MJOINT": ("-",), "LJOINT": ("-",)}


def label(base, cells, n, *, gates, ensembles, combined_present, assembled_present, engineering=False, prefreeze_stop=None, teacher_only=True):
    """gates: None (record missing) or {name: True/False}; ensembles[r]: None (missing) / 'nan' / 'equal' / 'differ';
    combined_present[(r, group, variant)] -> bool; assembled_present[r] -> {'M-i-separate': bool, 'L-sep': bool} or None."""
    eng = engineering
    inc = False
    if gates is None or not gates:
        inc = True
    else:
        for gname in REQUIRED_GATES:
            if gname not in gates:
                inc = True
            elif gates[gname] is not True and gname in ENG_GATES:
                eng = True
    for r in range(n):
        e = ensembles[r]
        if e == "differ":
            eng = True
        elif e in (None, "nan"):
            inc = True
    if eng:
        return 1
    for r in range(n):
        for g, vs in REGISTRY_GROUPS:
            for v in vs:
                c = cells.get((r, g, v))
                if c is None or c.status != "completed":
                    return 2
    if inc:
        return 2
    for (r, g, v), present in combined_present.items():
        if not present:
            c = cells.get((r, g, v))
            if g == "MII" and c is not None and c.rejected:
                continue  # R6 auditor reading
            return 2
    for r in range(n):
        a = assembled_present.get(r)
        if a is not None and not all(a.values()):
            return 2
    if prefreeze_stop:
        return 3
    neg = []
    for r in range(n):
        for o in ORDERS:
            G = G_full(base, cells[(r, "ST1", o)], "E_" + o[0])
            neg.append(G != UNDEF and G < 0.25)
    if all(neg):
        return 4
    failed, ctl_ne = controls(base, cells)
    if failed:
        return 5
    cls = {m: {o: mech_class(base, cells, n, m, o) for o in ORDERS} for m in MECH}
    AR = "ACQUIRES-AND-RETAINS"
    maf_ar = all(cls["M-append-frozen"][o] == AR for o in ORDERS)
    mii_ar = all(cls["M-ii"][o] == AR for o in ORDERS)
    gmaf = [gen_status(cells, n, "MAF", o) for o in ORDERS]
    gmii = [gen_status(cells, n, "MII", o) for o in ORDERS]
    pos = teacher_only and not ctl_ne
    if maf_ar and pos and "fails" in gmaf:
        return 6
    if maf_ar and mii_ar and pos and all(x == "holds" for x in gmaf) and all(x == "holds" for x in gmii):
        return 7
    if maf_ar and pos and all(x == "holds" for x in gmaf):
        return 8
    if all(cls["M-append-frozen"][o] == "FORGETS" for o in ORDERS):
        return 9
    if all(cls["M-append-frozen"][o] == "NO-NEW-CAPABILITY" for o in ORDERS):
        return 10
    if sum(cls["M-append-frozen"][o] == AR for o in ORDERS) == 1:
        return 11
    return 12


# ---------------------------------------------------------------------------------------------------------------------
# Combined-tasks addendum s8 (COMPOSES), from the addendum's text only.
def comp_h(sK, sS, s0K, s0S, tS):
    """One answer a of one cell. Returns (H or None, reason). Defined iff all finite, teacher gap tS - s0S >= 0.30
    and G_a^C = (sS - s0S)/(tS - s0S) >= 0.50. H = (sK - max(s0K, s0S)) / (sS - s0S)."""
    if not fin(sK, sS, s0K, s0S, tS):
        return None, "undefined score"
    tg = tS - s0S
    if tg < 0.30:
        return None, "teacher gap below 0.30"
    G = (sS - s0S) / tg
    if G < 0.50:
        return None, "single-task gap below 0.50"
    return (sK - max(s0K, s0S)) / (sS - s0S), ""


def comp_class(cells_by_order, rejected=False):
    """cells_by_order: {order: [cell or None per replicate]}, a cell = {lang: (sK, sS, s0K, s0S, tS)}.
    First match wins: NOT_EVALUATED / COMPOSES / DOES NOT COMPOSE / COMPOSITION INCONCLUSIVE."""
    H = {}
    if rejected:
        return "NOT_EVALUATED"
    for o, cells in cells_by_order.items():
        if not cells:
            return "NOT_EVALUATED"
        H[o] = []
        for c in cells:
            if c is None:
                return "NOT_EVALUATED"
            hs = {}
            for a in TASKS:
                h, _why = comp_h(*c[a])
                if h is None:
                    return "NOT_EVALUATED"
                hs[a] = h
            H[o].append(hs)
    if all(all(h[a] >= 0.80 for a in TASKS) for hs in H.values() for h in hs):
        return "COMPOSES"
    for o, hs in H.items():
        for a in TASKS:
            if all(h[a] < 0.50 for h in hs):
                return "DOES NOT COMPOSE"
    return "COMPOSITION INCONCLUSIVE"


# ---- C1 / C2 construction from the addendum text (s3, s4, s5, s6) -----------------------------------------------------
def c1_pairs(sigma):
    """Item j: s1 = sigma[j], s2 = sigma[(j+1) mod n]; T1 = A for even j, B for odd j."""
    n = len(sigma)
    return [(j, sigma[j], sigma[(j + 1) % n], "A" if j % 2 == 0 else "B", "B" if j % 2 == 0 else "A") for j in range(n)]


def tested_items(kind, pairs_or_n):
    """{lang: [sentence index]} on which the language is tested: C2 all items; C1 the items where it is the second answer."""
    if kind == "C2":
        return {a: list(range(pairs_or_n)) for a in TASKS}
    out = {"A": [], "B": []}
    for j, i1, i2, t1, t2 in pairs_or_n:
        out[t2].append(i2)
    return out
