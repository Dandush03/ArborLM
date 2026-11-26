# ruff: noqa  (auditor's script, recorded as run except for this line)
# ruff: noqa
"""Audit 20 (P10-I-S2 Part T): independent recomputation of the registered lines.

Stdlib only. Reads item_records.json (per-item chrF) and registry.json read-only.
Does not import any arborlm or studies.* module. Rules are typed from ADR-0025 section 8
as written (thresholds: 0.50, 0.25, 0.30, 0.80, 0.03, 0.90, 0.70, 0.05, 0.02).
Edge cells are additionally checked with exact rational arithmetic and with the opposite strictness.
Usage: python3 -I recompute_labels.py <run_dir>
"""
import json
import math
import sys
from fractions import Fraction

RUN = sys.argv[1]
items = json.load(open(f"{RUN}/item_records.json"))["items"]
reg = json.load(open(f"{RUN}/registry.json"))

# ---- 1. means from per-item scores, compared with the registry ----
n_exact = n_close = n_both = 0
worst = 0.0
def gen_increase(rec):
    g = rec["gen"]
    d = {"marker": [], "ordinary": []}
    for a, b, st in zip(g["nll_arm"], g["nll_base"], g["strata"]):
        d[st].append(a - b)
    return 0.5 * math.fsum(d["marker"]) / len(d["marker"]) + 0.5 * math.fsum(d["ordinary"]) / len(d["ordinary"])


gen_detail = []
for k, rec in items.items():
    if "gen" in rec:
        g = rec["gen"]
        inc = gen_increase(rec)
        gen_detail.append((k, len(g["nll_arm"]), sum(x == "marker" for x in g["strata"]), max(abs(a - b) for a, b in zip(g["nll_arm"], g["nll_base"])), sorted(set(g["preds"])), inc, reg.get(k)))
        continue
    if "items" not in rec:
        continue
    vals = rec["items"]
    m = math.fsum(vals) / len(vals)
    if k in reg:
        n_both += 1
        d = abs(m - reg[k])
        worst = max(worst, d)
        n_exact += m == reg[k]
        n_close += d <= 1e-12
print(f"item records: {len(items)}; registry keys: {len(reg)}; keys in both: {n_both}; item means == registry exactly: {n_exact}; within 1e-12: {n_close}; worst |diff| {worst:.3e}")
nonfinite = [k for k, v in reg.items() if isinstance(v, float) and not math.isfinite(v)]
nonfinite += [k for k, r in items.items() if any(not math.isfinite(x) for x in r.get("items", []))]
nonfinite += [k for k, r in items.items() if "gen" in r and any(not math.isfinite(x) for x in r["gen"]["nll_arm"] + r["gen"]["nll_base"])]
print("non-finite values:", nonfinite)
lens = {}
for k, r in items.items():
    if "items" in r:
        lens.setdefault(len(r["items"]), []).append(k.split("|")[-1])
print("item-record lengths:", {n: sorted(set(v)) for n, v in lens.items()})


print("GEN records:", len(gen_detail), "window counts", sorted({(n, m) for _, n, m, _, _, _, _ in gen_detail}), "max |nll_arm-nll_base|", max(x[3] for x in gen_detail), "route preds seen", sorted({p for x in gen_detail for p in x[4]}), "max own increase", max(x[5] for x in gen_detail), "registry values", sorted({x[6] for x in gen_detail}))


def s(key):
    """Mean of item scores (own fsum), falling back to registry only if no item record."""
    if key in items and "gen" in items[key]:
        return gen_increase(items[key])
    if key in items:
        v = items[key]["items"]
        return math.fsum(v) / len(v)
    return reg[key]


CAPS = {"A": "E_A", "B": "E_B"}
S0 = {c: s(f"S0|-|-|s:{p}") for c, p in CAPS.items()}
T = {c: s(f"TEACHER|-|-|s:{p}") for c, p in CAPS.items()}
S0sub = {c: s(f"S0|-|-|sub:own:{p}") for c, p in CAPS.items()}
Tsub = {c: s(f"TEACHER|-|-|sub:own:{p}") for c, p in CAPS.items()}
den = {c: T[c] - S0[c] for c in CAPS}
densub = {c: Tsub[c] - S0sub[c] for c in CAPS}
print("S0", S0, "TEACHER", T, "den", den, "den_sub", densub)
assert all(v >= 0.30 for v in den.values()), "full-panel gap undefined"
assert all(v >= 0.30 for v in densub.values()), "subsample gap undefined"


def G(arm, order, r, cap):
    return (s(f"{arm}|{order}|{r}|s:{CAPS[cap]}") - S0[cap]) / den[cap]


def Gsub(arm, order, r, cap, kind):
    return (s(f"{arm}|{order}|{r}|sub:{kind}:{CAPS[cap]}") - S0sub[cap]) / densub[cap]


def ctrl_ok(arm, order, r, cap):
    own = Gsub(arm, order, r, cap, "own")
    val = Gsub(arm, order, r, cap, "value")
    code = Gsub(arm, order, r, cap, "code")
    mk = Gsub(arm, order, r, cap, "marker")
    margin = own - max(val, code)
    return margin >= 0.30 and mk <= 0.25, dict(own=own, value=val, code=code, marker=mk, margin=margin)


CELLS = [(r, o) for r in (0, 1, 2) for o in ("AB", "BA")]
first = {"AB": "A", "BA": "B"}
second = {"AB": "B", "BA": "A"}
other = {"AB": "BA", "BA": "AB"}

rows = {}
for r, o in CELLS:
    f, sc = first[o], second[o]
    c = {}
    c["G_first_M1"] = G("M1", o, r, f)
    ok1, ctl1 = ctrl_ok("M1", o, r, f)
    c["ctl1"] = ctl1
    c["ACQ1"] = c["G_first_M1"] >= 0.50 and ok1
    c["G_second_Mapp"] = G("M-append", o, r, sc)
    c["G_M1_other"] = G("M1", other[o], r, sc)
    ok2, ctl2 = ctrl_ok("M-append", o, r, sc)
    c["ctl2"] = ctl2
    c["ACQ2"] = c["G_second_Mapp"] >= 0.50 and c["G_second_Mapp"] >= 0.80 * c["G_M1_other"] and ok2
    evaluable = c["G_first_M1"] >= 0.50
    c["F"] = s(f"M1|{o}|{r}|s:{CAPS[f]}") - s(f"M-append|{o}|{r}|s:{CAPS[f]}")
    c["rho"] = G("M-append", o, r, f) / c["G_first_M1"] if evaluable else None
    c["RET"] = evaluable and c["F"] <= 0.03 and c["rho"] >= 0.90
    c["rho_Mseq"] = G("M-seq", o, r, f) / c["G_first_M1"] if evaluable else None
    c["G_second_Mseq"] = G("M-seq", o, r, sc)
    c["pressure"] = evaluable and c["G_second_Mseq"] >= 0.50 and c["rho_Mseq"] < 0.90
    c["G_first_D1"] = G("D1", o, r, f)
    devaluable = c["G_first_D1"] >= 0.50
    c["G_second_Dapp"] = G("D-append", o, r, sc)
    c["G_second_Dseq"] = G("D-seq", o, r, sc)
    c["rho_Dapp"] = G("D-append", o, r, f) / c["G_first_D1"] if devaluable else None
    c["rho_Dseq"] = G("D-seq", o, r, f) / c["G_first_D1"] if devaluable else None
    c["dG"] = c["G_second_Mapp"] - c["G_second_Dapp"]
    c["dG_seq"] = c["G_second_Mseq"] - c["G_second_Dseq"]
    c["drho_seq"] = (c["rho_Mseq"] - c["rho_Dseq"]) if (evaluable and devaluable) else None
    rows[f"{r}{o}"] = c

cf = []
for k in reg:
    p = k.split("|")
    if p[0] in ("M1", "M-append", "M-seq", "M-ii", "M-joint") and len(p) == 4 and p[3].startswith("sub:") and p[3].split(":")[1] in ("value", "code"):
        cap = "A" if p[3].endswith("E_A") else "B"
        cf.append(((s(k) - S0sub[cap]) / densub[cap], k))
cf.sort(reverse=True)
print("largest permuted-control G:", [(round(g, 4), k) for g, k in cf[:3]], "count", len(cf))
control_failed = any(g >= 0.50 for g, _ in cf)


def fmt(x):
    return "None" if x is None else f"{x:.6f}"


print("\ncell  G1(M1)  ACQ1  G2(Mapp)  0.8*G(M1oth)  ACQ2  F  rho  RET  G2(Mseq)  rho(Mseq)  pressure  dG(Mapp-Dapp)  dG(seq)  drho(seq)")
for k, c in rows.items():
    print(k, fmt(c["G_first_M1"]), c["ACQ1"], fmt(c["G_second_Mapp"]), fmt(0.8 * c["G_M1_other"]), c["ACQ2"], fmt(c["F"]), fmt(c["rho"]), c["RET"], fmt(c["G_second_Mseq"]), fmt(c["rho_Mseq"]), c["pressure"], fmt(c["dG"]), fmt(c["dG_seq"]), fmt(c["drho_seq"]))
print("\ncontrol detail (ACQ1 on M1 first; ACQ2 on M-append second):")
for k, c in rows.items():
    print(k, {a: round(b, 4) for a, b in c["ctl1"].items()}, {a: round(b, 4) for a, b in c["ctl2"].items()})
print("dense side:")
for k, c in rows.items():
    print(k, "G1(D1)", fmt(c["G_first_D1"]), "G2(Dapp)", fmt(c["G_second_Dapp"]), "G2(Dseq)", fmt(c["G_second_Dseq"]), "rho(Dapp)", fmt(c["rho_Dapp"]), "rho(Dseq)", fmt(c["rho_Dseq"]))

print("\nexact edge check of G_second(M-append) against 0.50 (Fraction of the stored doubles; registry means):")
for k, c in rows.items():
    r, o = int(k[0]), k[1:]
    sc = second[o]
    exact = (Fraction(reg[f"M-append|{o}|{r}|s:{CAPS[sc]}"]) - Fraction(reg[f"S0|-|-|s:{CAPS[sc]}"])) / (Fraction(reg[f"TEACHER|-|-|s:{CAPS[sc]}"]) - Fraction(reg[f"S0|-|-|s:{CAPS[sc]}"]))
    print(k, f"G={float(exact):.10f}", " exact>=0.5:", exact >= Fraction(1, 2), " float>=0.5:", c["G_second_Mapp"] >= 0.5, " float>0.5:", c["G_second_Mapp"] > 0.5,
          f" margin to 0.5: {float(exact) - 0.5:+.6f}", f" margin to 0.8*G(M1 other): {c['G_second_Mapp'] - 0.8 * c['G_M1_other']:+.6f}",
          f" ctl margin-0.30: {c['ctl2']['margin'] - 0.30:+.4f} marker-0.25: {c['ctl2']['marker'] - 0.25:+.4f}")

V = list(rows.values())
if all(c["G_first_M1"] < 0.25 for c in V) or all(c["G_second_Mapp"] < 0.25 for c in V):
    acq = "ACQUISITION-NEGATIVE"
elif control_failed:
    acq = "ACQUISITION-INCONCLUSIVE: CONTROL-FAILED"
elif all(c["ACQ1"] and c["ACQ2"] for c in V):
    acq = "ACQUISITION-POSITIVE"
else:
    acq = "ACQUISITION-INCONCLUSIVE"
passing = {"ACQ1": {o: [r for r in (0, 1, 2) if rows[f"{r}{o}"]["ACQ1"]] for o in ("AB", "BA")},
           "ACQ2": {o: [r for r in (0, 1, 2) if rows[f"{r}{o}"]["ACQ2"]] for o in ("AB", "BA")}}

ev = [c for c in V if c["rho"] is not None]
if len(ev) >= 4 and all(c["rho"] < 0.70 for c in ev):
    ret = "RETENTION-NEGATIVE: FORGETTING"
elif not all(c["ACQ1"] for c in V):
    ret = "NOT EVALUABLE: FIRST NOT ACQUIRED"
elif any(c["G_second_Mapp"] < 0.50 for c in V):
    ret = "RETENTION-INCONCLUSIVE: NOT CHALLENGED — SECOND NOT ACQUIRED"
elif sum(c["pressure"] for c in V) < 4:
    ret = "RETENTION-INCONCLUSIVE: NOT CHALLENGED — NO FORGETTING PRESSURE"
elif all(c["RET"] for c in V):
    ret = "RETENTION-POSITIVE"
else:
    ret = "RETENTION-INCONCLUSIVE"
neg_zone = sum(1 for c in ev if c["rho"] < 0.70)
pressure_count = sum(c["pressure"] for c in V)

gen_vals = [s(f"M-append|{o}|{r}|gen:{pos}") for r, o in CELLS for pos in ("token64", "first_marker")]
gen = "PRESERVED" if all(math.isfinite(x) and x <= 0.02 for x in gen_vals) else "NOT PRESERVED/NOT EVALUABLE"


def pair_label(ds):
    if all(d >= 0.05 for d in ds):
        return "MEMORY AHEAD"
    if all(d <= -0.05 for d in ds):
        return "DENSE AHEAD"
    if all(abs(d) < 0.05 for d in ds):
        return "NOT DISTINGUISHED"
    return "MIXED"


ad_acq = pair_label([c["dG"] for c in V])
guard = [k for k, c in rows.items() if c["rho"] is None or c["rho_Dapp"] is None or c["G_second_Mapp"] < 0.5 or c["G_second_Dapp"] < 0.5]
ad_ret = "NOT EVALUABLE" if guard else pair_label([c["rho"] - c["rho_Dapp"] for c in V])
seq_acq = pair_label([c["dG_seq"] for c in V])
guard_seq = [k for k, c in rows.items() if c["rho_Mseq"] is None or c["rho_Dseq"] is None or c["G_second_Mseq"] < 0.5 or c["G_second_Dseq"] < 0.5]
seq_ret = "NOT EVALUABLE" if guard_seq else pair_label([c["drho_seq"] for c in V])
seq_ret_unguarded = pair_label([c["drho_seq"] for c in V]) if all(c["drho_seq"] is not None for c in V) else None

look = {}
lk_suff = lk_adds = True
for r, o in CELLS:
    for cap in ("A", "B"):
        cands = {b: s(f"{b}|-|{r}|s:{CAPS[cap]}") for b in ("R-gloss", "R-gloss-icl", "R-nn", "R-icl", "E-table")}
        bname = max(cands, key=cands.get)
        b = cands[bname]
        m = s(f"M-append|{o}|{r}|s:{CAPS[cap]}")
        look[f"{r}{o}/{cap}"] = (bname, b, m, b - (m - 0.03), m - b, cands["R-gloss"])
        lk_suff &= b >= m - 0.03
        lk_adds &= (m - b) >= 0.05
lookup = "LOOKUP SUFFICES" if lk_suff else ("MEMORY ADDS OVER LOOKUP" if lk_adds else "MIXED")
bnames = sorted({v[0] for v in look.values()})

mod_rows = {}
rejected = 0
for r, o in CELLS:
    f, sc = first[o], second[o]
    dcon_fail = any(s(f"M-ii|{o}|{r}|dcon:{cap}") < s(f"M-append|{o}|{r}|dcon:{cap}") - 0.02 for cap in ("A", "B"))
    rejected += dcon_fail
    g1 = G("M1", o, r, f)
    rho = G("M-ii", o, r, f) / g1 if g1 >= 0.5 else None
    Fm = s(f"M1|{o}|{r}|s:{CAPS[f]}") - s(f"M-ii|{o}|{r}|s:{CAPS[f]}")
    g2 = G("M-ii", o, r, sc)
    ok2, _ = ctrl_ok("M-ii", o, r, sc)
    acq2 = g2 >= 0.5 and g2 >= 0.8 * G("M1", other[o], r, sc) and ok2
    ret_ = rho is not None and Fm <= 0.03 and rho >= 0.90
    mod_rows[f"{r}{o}"] = dict(rho=rho, F=Fm, G2=g2, ACQ2=acq2, RET=ret_, floor=s(f"M-ii|{o}|{r}|modification"), dcon_fail=dcon_fail)
evm = [m for m in mod_rows.values() if m["rho"] is not None]
if rejected:
    mod = f"CONSOLIDATION-REJECTED ({rejected})"
elif len(evm) < 4:
    mod = "NOT EVALUABLE"
elif all(m["rho"] < 0.70 for m in evm):
    mod = "FORGETS UNDER MODIFICATION"
elif all(m["ACQ2"] and m["RET"] for m in mod_rows.values()) and any(m["floor"] < 0.10 for m in mod_rows.values()):
    mod = "RETENTION BY INERTIA"
elif all(m["ACQ2"] and m["RET"] for m in mod_rows.values()):
    mod = "RETAINS UNDER MODIFICATION"
else:
    mod = "INTERMEDIATE"

milestone = "SUPPORTED (append-frozen)" if (acq == "ACQUISITION-POSITIVE" and ret == "RETENTION-POSITIVE" and gen == "PRESERVED") else "NOT ESTABLISHED"
if lookup == "LOOKUP SUFFICES":
    milestone += " — a lookup baseline does as well: " + ("/".join(bnames))

print("\nLINES (independent recomputation):")
print(" MILESTONE:", milestone)
print(" ACQUISITION:", acq, "passing:", passing, "control_failed:", control_failed)
print(" RETENTION:", ret, "| evaluable", len(ev), "| in negative zone", neg_zone, "| forgetting-pressure cells", pressure_count)
print(" GENERAL-QUALITY:", gen, "max loss increase", max(gen_vals), "n", len(gen_vals))
print(" AGAINST-DENSE (M-append vs D-append): acquisition:", ad_acq, "; retention:", ad_ret, "| guard cells", guard)
print(" AGAINST-DENSE (M-seq vs D-seq): acquisition:", seq_acq, "; retention:", seq_ret, "| guard cells:", guard_seq, "| unguarded label:", seq_ret_unguarded)
print(" AGAINST-LOOKUP:", lookup, "best baselines:", bnames)
for k, v in look.items():
    print("   ", k, f"best={v[0]} b={v[1]:.4f} s(M-append)={v[2]:.4f} b-(s-0.03)={v[3]:+.4f} s-b={v[4]:+.4f} R-gloss={v[5]:.4f}")
print(" MODIFICATION:", mod)
for k, m in mod_rows.items():
    print("   ", k, {a: (round(b, 4) if isinstance(b, float) else b) for a, b in m.items()})
print(" per-cell dG (M-append - D-append):", [round(c["dG"], 3) for c in V])
print(" per-cell dG (M-seq - D-seq):", [round(c["dG_seq"], 3) for c in V])
print(" per-cell drho (M-seq - D-seq):", [None if c["drho_seq"] is None else round(c["drho_seq"], 3) for c in V])
print(" G_first(M1):", {k: round(c["G_first_M1"], 3) for k, c in rows.items()})
print(" G_second(M-append):", {k: round(c["G_second_Mapp"], 3) for k, c in rows.items()})
print(" ACQ1:", {k: c["ACQ1"] for k, c in rows.items()}, " ACQ2:", {k: c["ACQ2"] for k, c in rows.items()})
print(" F:", {k: round(c["F"], 3) for k, c in rows.items()})
print(" rho:", {k: round(c["rho"], 3) for k, c in rows.items()})
print(" APPEND COST change in G_first (M-append@append - M1):", {k: round(G("M-append@append", k[1:], int(k[0]), first[k[1:]]) - c["G_first_M1"], 3) for k, c in rows.items()})
