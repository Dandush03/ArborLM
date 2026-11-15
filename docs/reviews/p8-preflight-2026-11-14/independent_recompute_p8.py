"""Auditor's independent recomputation of every ADR-0015 section 7.2-7.4 / 8 quantity for P8.

Reads ONLY the raw per-cell records <eval_run>/cells/<label>/eval.json and
<sim_run>/cells/<label>/sim.json. Imports nothing from ``arborlm`` (the registry, the m formula,
the OLS fit, the guards, the classification and the decision map are written here from the ADR
text). Optionally compares with the implementation's analysis.json (``--analysis``).

Registry (ADR-0015 section 5): parents B101/O301, B102/O302, B103/O303; seeds 601, 602; cases
C01..C10; cell index = 20*parent + 10*seed + case; label ``b{B}-o{O}-s{seed}-C{nn}``.
Denominator is always 60 cells; a missing or incomplete cell makes every affected quantity
INCOMPLETE (never a smaller denominator).

Definitions used (ADR-0015 section 7.1-7.4):
  m(stream, L, R, tie) = (misses_warm - first_touch_warm) / (queries - queries // 2)
      (warm capacity misses per counted query, as P7-B's analysis derives it from p7b_sim counts)
  E(L) = m(actual, L) / mean_k m(null_k, L-FREQ); undefined if that null mean < 1/20.
  M-ratio, E-ratio: ratio of means over the six (parent, seed) pairs.
  rho_adj: OLS E = a + b x + d [case] on the 12 checkpoints, x = entropy_nats (= ln N_eff) of that
      panel's trace; rho = (a + b xbar + d) / (a + b xbar); undefined if a + b xbar <= 0, any E
      undefined, x ranges of case and reference do not overlap, or the design is singular.
  Pair counts: pairs with E_c < E_b; parent count: parents with mean_seeds E_c / mean_seeds E_b < 1.
  Retention: mean gain_c / mean gain_b (gain = NLL_disabled - NLL); association likewise with
      NLL_permuted - NLL. Lead ruling (ADR-0015 rev 3, pre-outcome): UNDEFINED when the baseline
      mean is <= 0, and an undefined retention FAILS the quality guard.
  U-ratio: geometric mean of N_eff,c / N_eff,b over pairs.
  Classification order 1-8 of section 7.4. If LOC holds and the U-ratio is undefined, rule 8
      (INTERMEDIATE) applies (lead ruling, rev 3).
  Decision map (lead ruling, rev 3): (a) iff C07 or C09 has an architecture advantage and the
      concentration controls do not bind; else (b) iff C06 or C08 is study-class LOCALITY-POSITIVE
      and beats optimized flat, no tree case has an architecture advantage and the controls do not
      bind; else (c). Non-replicated / INTERMEDIATE cases are listed as open questions only.
  Version 2 of this tool (see RECOMPUTE_TOOL_NOTE.md); v1 sha256 bf8d84c9…f068.

Exact arithmetic with fractions.Fraction (JSON floats enter as their exact binary value).

Usage:
  python independent_recompute_p8.py --eval-run E --sim-run S --out recompute_p8.json \
      [--analysis A/analysis.json]
Auditor tool (Claude Opus 5.5, independent of the implementation). Not Astra validation and not
human approval.
"""

import argparse
import hashlib
import json
import math
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

PARENTS = ((101, 301), (102, 302), (103, 303))
SEEDS = (601, 602)
CASES = tuple(f"C{i:02d}" for i in range(1, 11))
ARCH = {
    "C01": "flat", "C02": "fixed_tree", "C03": "learned_tree", "C04": "flat",
    "C05": "learned_tree", "C06": "flat", "C07": "learned_tree", "C08": "flat",
    "C09": "learned_tree", "C10": "learned_tree",
}  # fmt: skip
BASELINE = {"C04": "C01", "C05": "C03", "C06": "C01", "C07": "C03", "C08": "C01", "C09": "C03", "C10": "C03"}
FLAT_CP = {"C05": "C04", "C07": "C06", "C09": "C08"}
PANELS = ("A", "B")
SETTINGS = ((2, 32), (8, 8))
TIES = ("asc", "desc")
CONDS = [(r, c, t) for r, c in SETTINGS for t in TIES]
NULLS = ("null_1", "null_2", "null_3")
MAT, BLO, BHI, WOR = Fraction(4, 5), Fraction(9, 10), Fraction(11, 10), Fraction(5, 4)
QD, RET, FLOOR = Fraction(1, 200), Fraction(3, 4), Fraction(1, 20)
URET, UCOL = 0.8, 0.5

POS = "LOCALITY-POSITIVE (screening)"
RED = "LOCALITY WITH REDUCED UTILIZATION"
QF, COL, CONC, NOD, WRS, INT = (
    "QUALITY-FAILED", "COLLAPSED", "CONCENTRATION-ONLY", "NO DIFFERENCE", "WORSE", "INTERMEDIATE",
)  # fmt: skip
INC, NOTREP = "INCOMPLETE", "NOT REPLICATED ACROSS PANELS"


def label(b: int, o: int, s: int, c: str) -> str:
    return f"b{b}-o{o}-s{s}-{c}"


def index(b: int, s: int, c: str) -> int:
    return 20 * (b - 101) + 10 * SEEDS.index(s) + CASES.index(c)


def F(x: Any) -> Fraction:
    return Fraction(x)


def mean(xs: list[Fraction]) -> Fraction:
    return sum(xs, Fraction(0)) / len(xs)


class Cell:
    def __init__(self, ev: dict, sm: dict):
        self.ev, self.sm = ev, sm

    def nll(self, p: str, cond: str = "enabled", step: str = "step512") -> Fraction:
        return F(self.ev["nll"][step][cond][p])

    def gain(self, p: str) -> Fraction:
        return self.nll(p, "disabled") - self.nll(p)

    def assoc(self, p: str) -> Fraction:
        return self.nll(p, "values_permuted") - self.nll(p)

    def x(self, p: str) -> Fraction:
        return F(self.ev["traces"][p]["utilization"]["entropy_nats"])

    def neff(self, p: str) -> float:
        return float(self.ev["traces"][p]["utilization"]["n_eff"])

    def m(self, p: str, stream: str, layout: str, r: int, c: int, tie: str) -> Fraction:
        rec = self.sm["panels"][p]
        e = rec["streams"][stream][f"{layout}|R{r}"]["by_c"][str(c)][tie]
        q = int(rec["queries"])
        return Fraction(int(e["misses_warm"]) - int(e["first_touch_warm"]), q - q // 2)

    def e(self, p: str, layout: str, r: int, c: int, tie: str) -> Fraction | None:
        null = mean([self.m(p, s, "L-FREQ", r, c, tie) for s in NULLS])
        if null < FLOOR:
            return None
        return self.m(p, "actual", layout, r, c, tie) / null


def load(eval_run: Path, sim_run: Path) -> tuple[dict[str, Cell], list[dict]]:
    cells, missing = {}, []
    for b, o in PARENTS:
        for s in SEEDS:
            for c in CASES:
                lab = label(b, o, s, c)
                ep, sp = eval_run / "cells" / lab / "eval.json", sim_run / "cells" / lab / "sim.json"
                why = []
                ev = sm = None
                if not ep.is_file():
                    why.append("eval.json missing")
                else:
                    ev = json.loads(ep.read_text())
                    if ev.get("outcome") != "completed" or ev.get("label") != lab:
                        why.append("eval not completed / wrong label")
                    if ev.get("cell_index", index(b, s, c)) != index(b, s, c):
                        why.append("eval cell_index differs from registry")
                if not sp.is_file():
                    why.append("sim.json missing")
                else:
                    sm = json.loads(sp.read_text())
                    if sm.get("outcome") != "completed" or set(sm.get("panels", {})) != set(PANELS):
                        why.append("sim not completed for both panels")
                    elif ep.is_file() and sm.get("eval_json_sha256") != hashlib.sha256(ep.read_bytes()).hexdigest():
                        why.append("sim built from a different eval.json")
                if why:
                    missing.append({"label": lab, "reasons": why})
                else:
                    cells[lab] = Cell(ev, sm)
    return cells, missing


def solve3(A: list[list[Fraction]], y: list[Fraction]) -> list[Fraction] | None:
    """Cramer's rule on the 3x3 normal equations."""

    def det(m: list[list[Fraction]]) -> Fraction:
        return (
            m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
        )

    D = det(A)
    if D == 0:
        return None
    out = []
    for j in range(3):
        Aj = [[y[i] if k == j else A[i][k] for k in range(3)] for i in range(3)]
        out.append(det(Aj) / D)
    return out


def rho_adj(ec: list[Fraction], er: list[Fraction], xc: list[Fraction], xr: list[Fraction]) -> tuple[Fraction | None, str | None]:
    if max(min(xc), min(xr)) > min(max(xc), max(xr)):
        return None, "x ranges do not overlap"
    rows = [(Fraction(1), x, Fraction(0), y) for x, y in zip(xr, er)] + [
        (Fraction(1), x, Fraction(1), y) for x, y in zip(xc, ec)
    ]
    A = [[sum((r[i] * r[j] for r in rows), Fraction(0)) for j in range(3)] for i in range(3)]
    y = [sum((r[i] * r[3] for r in rows), Fraction(0)) for i in range(3)]
    sol = solve3(A, y)
    if sol is None:
        return None, "singular"
    a, b, d = sol
    xbar = mean(xr + xc)
    lvl = a + b * xbar
    if lvl <= 0:
        return None, "a + b xbar <= 0"
    return (lvl + d) / lvl, None


def pairs_of(cells: dict[str, Cell], case: str, ref: str) -> tuple[list[tuple[tuple[int, int, int], Cell, Cell]], list[str]]:
    out, miss = [], []
    for b, o in PARENTS:
        for s in SEEDS:
            lc, lr = label(b, o, s, case), label(b, o, s, ref)
            if lc in cells and lr in cells:
                out.append(((b, o, s), cells[lc], cells[lr]))
            else:
                miss += [x for x in (lc, lr) if x not in cells]
    return out, miss


def condition(pairs: list, p: str, r: int, c: int, t: str, lc: str, lr: str) -> dict[str, Any]:
    mc = [C.m(p, "actual", lc, r, c, t) for _, C, _ in pairs]
    mr = [R.m(p, "actual", lr, r, c, t) for _, _, R in pairs]
    out: dict[str, Any] = {"m_ratio": None if mean(mr) == 0 else mean(mc) / mean(mr)}
    out["pairs_m_lower"] = sum(1 for a, b in zip(mc, mr) if a < b)
    ec = [C.e(p, lc, r, c, t) for _, C, _ in pairs]
    er = [R.e(p, lr, r, c, t) for _, _, R in pairs]
    if any(v is None for v in ec + er):
        out.update(e_ratio=None, rho_adj=None, pairs_e_lower=None, parents_e_below_one=None, e_undefined=True)
        return out
    out["e_ratio"] = None if mean(er) == 0 else mean(ec) / mean(er)
    out["pairs_e_lower"] = sum(1 for a, b in zip(ec, er) if a < b)
    par = 0
    for b, o in PARENTS:
        idx = [i for i, (k, _, _) in enumerate(pairs) if k[:2] == (b, o)]
        num, den = mean([ec[i] for i in idx]), mean([er[i] for i in idx])
        par += den != 0 and num / den < 1
    out["parents_e_below_one"] = par
    xc = [C.x(p) for _, C, _ in pairs]
    xr = [R.x(p) for _, _, R in pairs]
    out["rho_adj"], out["rho_adj_reason"] = rho_adj(ec, er, xc, xr)
    return out


def quality(pairs: list, p: str) -> dict[str, Any]:
    d = [C.nll(p) - R.nll(p) for _, C, R in pairs]
    gc, gr = mean([C.gain(p) for _, C, _ in pairs]), mean([R.gain(p) for _, _, R in pairs])
    ac, ar = mean([C.assoc(p) for _, C, _ in pairs]), mean([R.assoc(p) for _, _, R in pairs])
    nc, nr = [C.neff(p) for _, C, _ in pairs], [R.neff(p) for _, _, R in pairs]
    u = None
    if all(v > 0 for v in nc + nr):
        u = math.exp(math.fsum(math.log(a / b) for a, b in zip(nc, nr)) / len(nc))
    gret = None if gr <= 0 else gc / gr  # rev 3: undefined when baseline mean <= 0
    aret = None if ar <= 0 else ac / ar
    dm = mean(d)
    above = sum(1 for x in d if x > QD)
    passes = None not in (gret, aret) and dm <= QD and above <= 1 and gret >= RET and aret >= RET
    return {
        "delta_nll_mean": dm, "pairs_above": above, "gain_retention": gret,
        "association_retention": aret, "u_ratio": u, "quality_passes": passes,
        "gain_baseline_nonpositive": gr <= 0, "association_baseline_nonpositive": ar <= 0,
    }  # fmt: skip


def compare(cells: dict[str, Cell], case: str, ref: str, p: str) -> dict[str, Any]:
    pairs, miss = pairs_of(cells, case, ref)
    if miss or len(pairs) != 6:
        return {"status": INC, "missing": miss}
    out: dict[str, Any] = {"status": "complete", "quality": quality(pairs, p), "tags": {}}
    tree_c, tree_r = ARCH[case] != "flat", ARCH[ref] != "flat"
    out["tags"]["L-COAX"] = {f"R{r}|C{c}|{t}": condition(pairs, p, r, c, t, "L-COAX", "L-COAX") for r, c, t in CONDS}
    if tree_c:
        lr = "L-BCOAX" if tree_r else "L-COAX"
        out["tags"]["L-BCOAX"] = {f"R{r}|C{c}|{t}": condition(pairs, p, r, c, t, "L-BCOAX", lr) for r, c, t in CONDS}
    return out


def le(x: Fraction | None, b: Fraction) -> bool:
    return x is not None and x <= b


def classify(comp: dict[str, Any]) -> str:
    if comp["status"] != "complete":
        return INC
    q = comp["quality"]
    conds = list(comp["tags"]["L-COAX"].values())
    if not q["quality_passes"]:
        return QF
    u = q["u_ratio"]
    if u is not None and u < UCOL:
        return COL
    loc = all(
        le(c["m_ratio"], MAT) and le(c["e_ratio"], MAT) and le(c["rho_adj"], MAT)
        and (c["pairs_e_lower"] or 0) >= 5 and c["parents_e_below_one"] == 3
        for c in conds
    )  # fmt: skip
    if loc:
        if u is None:
            return INT  # rule 5 needs LOC to fail; rule 8 covers the undefined U-ratio
        return POS if u >= URET else RED
    if all(le(c["m_ratio"], MAT) for c in conds):
        return CONC
    within = lambda x: x is not None and BLO <= x <= BHI  # noqa: E731
    if all(within(c["m_ratio"]) and within(c["e_ratio"]) for c in conds):
        return NOD
    ge = lambda x: x is not None and x >= WOR  # noqa: E731
    if all(ge(c["m_ratio"]) for c in conds) or all(ge(c["e_ratio"]) for c in conds):
        return WRS
    return INT


def all_three_le(comp_by_panel: dict[str, dict]) -> bool:
    for p in PANELS:
        comp = comp_by_panel[p]
        if comp["status"] != "complete":
            return False
        for c in comp["tags"]["L-COAX"].values():
            if not (le(c["m_ratio"], MAT) and le(c["e_ratio"], MAT) and le(c["rho_adj"], MAT)):
                return False
        if not le(comp["quality"]["delta_nll_mean"], QD):
            return False
    return True


def analyse(cells: dict[str, Cell], missing: list[dict]) -> dict[str, Any]:
    res: dict[str, Any] = {"cells_expected": 60, "cells_complete": len(cells), "missing": missing,
                           "study_status": "COMPLETE" if not missing else INC, "cases": {}}  # fmt: skip
    cls: dict[str, dict[str, str]] = {p: {} for p in PANELS}
    for case in CASES:
        ent: dict[str, Any] = {"panels": {}}
        refs = {}
        if case in BASELINE:
            refs["baseline"] = BASELINE[case]
        if case in FLAT_CP:
            refs["flat_counterpart"] = FLAT_CP[case]
        if case == "C10":
            refs["flat_counterpart_C06"], refs["flat_counterpart_C08"] = "C06", "C08"
        if case != "C01":
            refs["c01"] = "C01"
        for p in PANELS:
            pe = {name: compare(cells, case, ref, p) for name, ref in refs.items()}
            if case in BASELINE:
                cls[p][case] = classify(pe["baseline"])
                pe["class"] = cls[p][case]
            ent["panels"][p] = pe
        if case in BASELINE:
            a, b = cls["A"][case], cls["B"][case]
            study = a if a == b else NOTREP
            ent["study_class"] = study
            beats = study == POS and all_three_le({p: ent["panels"][p]["c01"] for p in PANELS})
            ent["beats_optimized_flat"] = beats
            if case in FLAT_CP:
                ent["architecture_advantage"] = beats and all_three_le(
                    {p: ent["panels"][p]["flat_counterpart"] for p in PANELS}
                )
            else:
                ent["architecture_advantage"] = False
        res["cases"][case] = ent
    bind = any(cls[p].get(c) == POS for p in PANELS for c in ("C04", "C05"))
    res["concentration_controls_bind"] = bind
    arch = [c for c in ("C07", "C09") if res["cases"][c]["architecture_advantage"]]
    flatpos = [
        c for c in ("C06", "C08")
        if res["cases"][c]["study_class"] == POS and res["cases"][c]["beats_optimized_flat"]
    ]
    tree_arch = [c for c in CASES if ARCH[c] != "flat" and res["cases"][c].get("architecture_advantage")]
    if res["study_status"] != "COMPLETE":
        dec = "none"
    elif arch and not bind:
        dec = "a"
    elif flatpos and not tree_arch and not bind:
        dec = "b"
    else:
        dec = "c"
    res["decision"] = dec
    res["open_questions"] = [
        c for c in BASELINE if res["cases"][c].get("study_class") in (NOTREP, INT)
    ]
    return res


def jsonable(o: Any) -> Any:
    if isinstance(o, Fraction):
        return {"value": float(o), "exact": f"{o.numerator}/{o.denominator}"}
    if isinstance(o, dict):
        return {k: jsonable(v) for k, v in o.items()}
    if isinstance(o, list | tuple):
        return [jsonable(v) for v in o]
    return o


# ---------------------------------------------------------------------------------- comparison
def num(x: Any) -> Fraction | float | None:
    if x is None:
        return None
    if isinstance(x, dict) and "exact" in x:
        if x["exact"] is None:
            return None
        n, d = x["exact"].split("/")
        return Fraction(int(n), int(d))
    if isinstance(x, Fraction | int | float):
        return x
    return None


def compare_with_impl(mine: dict[str, Any], impl: dict[str, Any]) -> dict[str, Any]:
    n, mism, maxd = 0, [], 0.0

    def chk(where: str, a: Any, b: Any, exact: bool = True) -> None:
        nonlocal n, maxd
        n += 1
        if isinstance(a, str | bool) or isinstance(b, str | bool) or a is None or b is None:
            if a != b:
                mism.append({"where": where, "auditor": str(a), "implementation": str(b)})
            return
        d = abs(float(a) - float(b))
        maxd = max(maxd, d)
        ok = (a == b) if exact else d <= 1e-12 * max(1.0, abs(float(b)))
        if not ok:
            mism.append({"where": where, "auditor": float(a), "implementation": float(b), "abs_diff": d})

    chk("study_status", mine["study_status"], impl["study_status"])
    chk("concentration_controls_bind", mine["concentration_controls_bind"], impl["concentration_controls_bind"])
    chk("decision", mine["decision"], impl["decision_inputs"]["section_8_option_indicated"])
    for case, ent in mine["cases"].items():
        ie = impl["cases"][case]
        if "study_class" in ent:
            chk(f"{case}.study_class", ent["study_class"], ie["study_classification"]["class"])
            chk(f"{case}.beats", ent["beats_optimized_flat"], ie["beats_optimized_flat"]["holds"])
            chk(f"{case}.arch", ent["architecture_advantage"], ie["architecture_advantage"]["holds"])
        for p in PANELS:
            pe, ip = ent["panels"][p], ie["panels"][p]
            if "class" in pe:
                chk(f"{case}.{p}.class", pe["class"], ip["classification"])
            for name, comp in pe.items():
                if name == "class":
                    continue
                icomp = ip["vs_baseline"] if name == "baseline" else ip["vs_other"].get(name)
                if icomp is None:
                    mism.append({"where": f"{case}.{p}.{name}", "auditor": "present", "implementation": "absent"})
                    continue
                chk(f"{case}.{p}.{name}.status", comp["status"], "complete" if icomp.get("status") == "complete" else INC)
                if comp["status"] != "complete" or icomp.get("status") != "complete":
                    continue
                q, iq = comp["quality"], icomp["quality"]
                w = f"{case}.{p}.{name}.quality"
                chk(w + ".delta_nll_mean", q["delta_nll_mean"], num({"exact": iq["delta_nll_mean_exact"]}))
                chk(w + ".pairs_above", q["pairs_above"], iq["pairs_delta_nll_above_0_005"])
                chk(w + ".gain_retention", q["gain_retention"], num(iq["gain_retention"]))
                chk(w + ".association_retention", q["association_retention"], num(iq["association_retention"]))
                chk(w + ".u_ratio", q["u_ratio"], iq["u_ratio"], exact=False)
                chk(w + ".passes", bool(q["quality_passes"]), iq["quality_guard"]["passes"])
                for tag, conds in comp["tags"].items():
                    itag = icomp["tags"].get(tag)
                    if itag is None:
                        mism.append({"where": f"{case}.{p}.{name}.{tag}", "auditor": "present", "implementation": "absent"})
                        continue
                    for key, c in conds.items():
                        ic = itag[key]
                        w2 = f"{case}.{p}.{name}.{tag}.{key}"
                        for f in ("m_ratio", "e_ratio", "rho_adj"):
                            chk(f"{w2}.{f}", c[f], num(ic[f]))
                        chk(f"{w2}.pairs_m_lower", c["pairs_m_lower"], ic["pairs_m_lower"])
                        if c["pairs_e_lower"] is not None:
                            chk(f"{w2}.pairs_e_lower", c["pairs_e_lower"], ic["pairs_e_lower"])
                            chk(f"{w2}.parents_e_below_one", c["parents_e_below_one"], ic["parents_e_below_one"])
                if set(comp["tags"]) != set(icomp["tags"]):
                    mism.append({"where": f"{case}.{p}.{name}.tags", "auditor": sorted(comp["tags"]), "implementation": sorted(icomp["tags"])})
    return {"compared_values": n, "max_abs_difference": maxd, "mismatch_count": len(mism), "mismatches": mism}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-run", type=Path, required=True)
    ap.add_argument("--sim-run", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--analysis", type=Path)
    args = ap.parse_args()
    cells, missing = load(args.eval_run, args.sim_run)
    mine = analyse(cells, missing)
    out: dict[str, Any] = {
        "tool": "independent_recompute_p8.py",
        "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "label": "auditor recomputation (Claude Opus 5.5); not Astra validation, not human approval",
        "result": jsonable(mine),
    }
    summary = {
        "study_status": mine["study_status"], "cells": f"{len(cells)}/60",
        "classes": {c: mine["cases"][c].get("study_class") for c in BASELINE},
        "per_panel": {c: [mine["cases"][c]["panels"][p].get("class") for p in PANELS] for c in BASELINE},
        "bind": mine["concentration_controls_bind"], "decision": mine["decision"],
    }  # fmt: skip
    if args.analysis:
        impl = json.loads(args.analysis.read_text())
        out["comparison"] = compare_with_impl(mine, impl)
        out["analysis_sha256"] = hashlib.sha256(args.analysis.read_bytes()).hexdigest()
        summary["comparison"] = {k: out["comparison"][k] for k in ("compared_values", "max_abs_difference", "mismatch_count")}
        summary["first_mismatches"] = out["comparison"]["mismatches"][:15]
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True))
    print(json.dumps(summary, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
