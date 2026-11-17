"""Re-check auditor C: compare studies/p10s2/analysis.analyze (label row, mechanism classes) with rules_v2 on random
synthetic records. Seeds 229101 (test range). Usage: <python> check_rules_v2.py <pin> <trials> <out.json>
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""

import json
import random
import sys
from collections import Counter
from pathlib import Path

PIN = sys.argv[1]
sys.path.insert(0, PIN)
sys.path.insert(0, PIN + "/src")
sys.path.insert(0, str(Path(__file__).parent))

from studies.p10s2 import analysis  # noqa: E402

import rules_v2 as S  # noqa: E402
import synth as Y  # noqa: E402

GVALS = [-0.1, 0.2, 0.24, 0.26, 0.45, 0.55, 0.6, 0.65, 0.75, 0.83, 0.95, 1.1, "nan", "missing"]
GENV = [0.001, 0.019, 0.02, 0.021, 0.05, "nan", None]


def good_comb():
    return Y.comb_record({"C1": {"A": 0.6, "B": 0.6}, "C2": {"A": 0.6, "B": 0.6}, "single": {"A": 0.62, "B": 0.62}})


def scenario(rng, n):
    base = {"s0": {}, "t": {}, "s0sub": {}, "tsub": {}}
    for p in ("E_A", "E_B"):
        base["s0"][p] = 0.1
        base["t"][p] = 0.9 if rng.random() > 0.03 else 0.35
        base["s0sub"][p] = 0.12
        base["tsub"][p] = 0.88 if rng.random() > 0.03 else 0.4
    cells = {}
    for r in range(n):
        for (g, v), (ga, gb) in Y.TEMPLATE.items():
            panels = {"E_A": ga, "E_B": gb}
            abl = None
            if g in Y.MEMORY:
                abl = {p: {"unablated": panels[p], "value_perm": 0.05, "code_perm": 0.08, "marker_only": 0.1} for p in ("E_A", "E_B")}
            cells[(r, g, v)] = S.Cell(panels=panels, abl=abl, gen=(0.001, 0.001) if g in Y.GEN else None)
    gates = {g: True for g in Y.GATES}
    ensembles = ["equal"] * n
    combined = {(r, g, v): True for r in range(n) for g, vs in S.COMP.items() for v in vs}
    assembled = {r: {"M-i-separate": True, "L-sep": True} for r in range(n)}
    keys = list(cells)
    k = rng.choice([0, 0, 1, 1, 2, 3, 5, 8])
    for _ in range(k):
        what = rng.random()
        key = rng.choice(keys)
        c = cells[key]
        if what < 0.30:
            p = rng.choice(["E_A", "E_B"])
            c.panels[p] = rng.choice(GVALS)
            if c.abl is not None and p in c.abl and rng.random() < 0.7:
                c.abl[p]["unablated"] = c.panels[p]
        elif what < 0.42 and c.abl is not None:
            p = rng.choice(["E_A", "E_B"])
            if p in c.abl:
                kind = rng.choice(["value_perm", "code_perm", "marker_only", "unablated"])
                c.abl[p][kind] = rng.choice([0.0, 0.2, 0.3, 0.45, 0.55, 0.62, "nan", 0.9])
        elif what < 0.48 and c.abl is not None:
            u = rng.random()
            if u < 0.33:
                c.abl = None
            elif u < 0.66:
                c.abl.pop(rng.choice(["E_A", "E_B"]), None)
            else:
                p = rng.choice(list(c.abl) or ["E_A"])
                if p in c.abl:
                    c.abl[p].pop(rng.choice(["value_perm", "code_perm", "marker_only", "unablated"]), None)
        elif what < 0.62:
            if c.gen is not None or rng.random() < 0.2:
                c.gen = (rng.choice(GENV), rng.choice(GENV)) if rng.random() < 0.9 else None
        elif what < 0.68:
            c.status = rng.choice(["failed", "skipped_dependency", "missing"])
        elif what < 0.74:
            if key[1] == "MII":
                c.rejected = rng.random() < 0.5
                c.below_floor = rng.random() < 0.5
        elif what < 0.82:
            u = rng.random()
            if u < 0.1:
                gates = None
            elif gates is not None:
                gname = rng.choice(Y.GATES)
                if u < 0.55:
                    gates.pop(gname, None)
                else:
                    gates[gname] = False
        elif what < 0.88:
            ensembles[rng.randrange(n)] = rng.choice([None, "nan", "differ"])
        elif what < 0.94:
            ck = rng.choice(list(combined))
            combined[ck] = False
        else:
            r = rng.randrange(n)
            assembled[r][rng.choice(["M-i-separate", "L-sep"])] = False
    return base, cells, gates, ensembles, combined, assembled


def numeric(base, cells):
    out = {}
    for key, c in cells.items():
        panels = {p: Y.to_score(base, p, G) for p, G in c.panels.items() if G != "missing"}
        abl = None if c.abl is None else {p: {k: Y.to_score(base, p, G, sub=True) for k, G in a.items()} for p, a in c.abl.items()}
        gen = None if c.gen is None else tuple(float("nan") if x == "nan" else x for x in c.gen)
        out[key] = S.Cell(status=c.status, panels=panels, abl=abl, gen=gen, rejected=c.rejected, below_floor=c.below_floor)
    return out


def main():
    trials = int(sys.argv[2])
    rng = random.Random(229101)
    rows_impl, rows_mine = Counter(), Counter()
    dis, crashes = [], []
    gc = good_comb()
    for t in range(trials):
        n = rng.choice([3, 4])
        base, cells, gates, ens, comb_p, asm_p = scenario(rng, n)
        nc = numeric(base, cells)
        combined = {k: (gc if v else None) for k, v in comb_p.items()}
        assembled = {r: {"label": "BY CONSTRUCTION", **{a: ({"E_A": {"mean": 0.5}, "E_B": {"mean": 0.5}} | ({"combined": gc} if ok else {})) for a, ok in asm_p[r].items()}} for r in range(n)}
        study = Y.serialize(base, nc, n, gates=gates, ensembles=ens, combined=combined, assembled=assembled, stage0_comb=gc, ens_comb=gc)
        try:
            out = analysis.analyze(study)
        except Exception as e:
            crashes.append((t, repr(e)[:300]))
            continue
        mine = S.label(base, nc, n, gates=gates, ensembles=ens, combined_present={k: v for k, v in comb_p.items()}, assembled_present=asm_p)
        rows_impl[out["label_row"]] += 1
        rows_mine[mine] += 1
        ci = {m: {o: out["classes"][m][o]["class"] for o in S.ORDERS} for m in S.MECH}
        cm = {m: {o: S.mech_class(base, nc, n, m, o) for o in S.ORDERS} for m in S.MECH}
        if out["label_row"] != mine or ci != cm:
            dis.append({"trial": t, "impl_row": out["label_row"], "auditor_row": mine, "impl_classes": ci, "auditor_classes": cm,
                        "incomplete": out["incomplete"][:6], "engineering": out["engineering"][:4], "gates": gates, "ensembles": ens,
                        "combined_missing": [str(k) for k, v in comb_p.items() if not v], "assembled": asm_p})
    print("trials", trials)
    print("rows (impl):", dict(sorted(rows_impl.items())))
    print("rows (auditor):", dict(sorted(rows_mine.items())))
    print("crashes:", len(crashes), crashes[:5])
    print("disagreements (label row or any class):", len(dis))
    kinds = Counter((d["impl_row"], d["auditor_row"]) for d in dis)
    print("disagreement (impl_row, auditor_row) counts:", dict(kinds))
    Path(sys.argv[3]).write_text(json.dumps({"disagreements": dis[:60], "crashes": crashes[:40]}, indent=1, default=str))


if __name__ == "__main__":
    main()
