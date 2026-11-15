"""Compare studies/p10s2/analysis.analyze (label row, mechanism classes) with the auditor's spec_rules on random
synthetic records covering every row: missing, failed, non-finite cells, rejected consolidations, inertia cells,
undefined gaps, absent ablation sections. Seeds: 229501.. (test range). Claude (Opus 5.5) review; Astra review:
NOT_PERFORMED; not a human approval."""

import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

PIN = sys.argv[1]
sys.path.insert(0, PIN)
sys.path.insert(0, PIN + "/src")
sys.path.insert(0, str(Path(__file__).parent))

from studies.p10s2 import analysis  # noqa: E402

import spec_rules as S  # noqa: E402

TEMPLATE = {
    ("ST1", "AB"): (0.9, 0.0), ("ST1", "BA"): (0.0, 0.9),
    ("MAF", "AB"): (0.88, 0.85), ("MAF", "BA"): (0.85, 0.88),
    ("MII", "AB"): (0.88, 0.85), ("MII", "BA"): (0.85, 0.88),
    ("MSEQ", "AB"): (0.1, 0.85), ("MSEQ", "BA"): (0.85, 0.1),
    ("LORA1", "AB"): (0.9, 0.0), ("LORA1", "BA"): (0.0, 0.9),
    ("LSEQ", "AB"): (0.1, 0.9), ("LSEQ", "BA"): (0.9, 0.1),
    ("ETABLE", "A"): (0.8, 0.0), ("ETABLE", "B"): (0.0, 0.8),
    ("MAGOLD", "A"): (0.9, 0.0), ("MAGOLD", "B"): (0.0, 0.9),
    ("MJOINT", "-"): (0.85, 0.85), ("LJOINT", "-"): (0.9, 0.9),
}
MEMORY = ("ST1", "MAF", "MII", "MSEQ", "MJOINT", "MAGOLD")
GEN = ("ST1", "MAF", "MII", "MSEQ", "MJOINT", "LSEQ")
GVALS = [-0.1, 0.2, 0.24, 0.26, 0.45, 0.55, 0.6, 0.65, 0.75, 0.83, 0.95, 1.1, "nan", "missing"]


def scenario(rng, n):
    base = {"s0": {}, "t": {}, "s0sub": {}, "tsub": {}}
    for p in ("E_A", "E_B"):
        base["s0"][p] = 0.1
        base["t"][p] = 0.9 if rng.random() > 0.04 else 0.35
        base["s0sub"][p] = 0.12
        base["tsub"][p] = 0.88 if rng.random() > 0.04 else 0.4
    cells = {}
    for r in range(n):
        for (g, v), (ga, gb) in TEMPLATE.items():
            panels = {"E_A": ga, "E_B": gb}
            abl = None
            if g in MEMORY:
                abl = {p: {"unablated": panels[p], "value_perm": 0.05, "code_perm": 0.08, "marker_only": 0.1} for p in ("E_A", "E_B")}
            c = S.Cell(panels=panels, abl=abl, gen=0.001 if g in GEN else None)
            cells[(r, g, v)] = c
    # perturbations
    k = rng.choice([0, 0, 1, 2, 3, 5, 8])
    keys = list(cells)
    for _ in range(k):
        key = rng.choice(keys)
        c = cells[key]
        what = rng.random()
        if what < 0.45:
            p = rng.choice(["E_A", "E_B"])
            c.panels[p] = rng.choice(GVALS)
            if c.abl is not None and rng.random() < 0.7:
                c.abl[p]["unablated"] = c.panels[p]
        elif what < 0.65 and c.abl is not None:
            p = rng.choice(["E_A", "E_B"])
            kind = rng.choice(["value_perm", "code_perm", "marker_only", "unablated"])
            c.abl[p][kind] = rng.choice([0.0, 0.2, 0.3, 0.45, 0.55, 0.62, "nan", 0.9])
        elif what < 0.70 and c.abl is not None and not __import__("os").environ.get("NO_ABSENT"):
            if rng.random() < 0.5:
                c.abl = None
            else:
                del c.abl[rng.choice(["E_A", "E_B"])]
        elif what < 0.80:
            c.gen = rng.choice([0.001, 0.019, 0.021, 0.05, "nan", None])
        elif what < 0.88:
            c.status = rng.choice(["failed", "skipped_dependency", "missing"])
        else:
            if key[1] == "MII":
                c.rejected = rng.random() < 0.5
                c.below_floor = rng.random() < 0.5
    return base, cells


def to_score(base, p, G, sub=False):
    if G in ("nan", "missing"):
        return float("nan")
    s0 = base["s0sub" if sub else "s0"][p]
    return s0 + G * (0.8 if not sub else 0.76)


def numeric_cells(base, cells):
    """Convert G-valued abstract cells into score-valued Cells for spec_rules."""
    out = {}
    for key, c in cells.items():
        panels = {p: to_score(base, p, G) for p, G in c.panels.items() if G != "missing"}
        abl = None if c.abl is None else {p: {k: to_score(base, p, G, sub=True) for k, G in a.items()} for p, a in c.abl.items()}
        gen = float("nan") if c.gen == "nan" else c.gen
        out[key] = S.Cell(status=c.status, panels=panels, abl=abl, gen=gen, rejected=c.rejected, below_floor=c.below_floor)
    return out


def serialize(base, ncells, n):
    def pn(x):
        return {"mean": "nan" if isinstance(x, float) and math.isnan(x) else x, "exact_rate": 0.0}

    reps = []
    for r in range(n):
        cs = {}
        for (rr, g, v), c in ncells.items():
            if rr != r:
                continue
            label = f"r{r}/{g}/{v}"
            if c.status == "missing":
                continue
            snap = {"panels": {p: pn(x) for p, x in c.panels.items()}}
            if c.abl is not None:
                snap["ablations"] = {p: {k: pn(x) for k, x in a.items()} | {"off": pn(0.1), "words_only": pn(0.1)} for p, a in c.abl.items()}
            if g in GEN and c.gen is not None:
                snap["gen"] = {"loss_increase": "nan" if isinstance(c.gen, float) and math.isnan(c.gen) else c.gen}
            rec = {"label": label, "status": c.status, "train": [{"wall_seconds": 10.0}], "scores": {label: snap} if c.status == "completed" else {},
                   "extras": {"consolidation": {"rejected": c.rejected, "below_floor": c.below_floor}} if g == "MII" else {}}
            cs[label] = rec
        reps.append({"cells": cs, "assembled": {}, "retrieval": {}, "routers": {}, "ensemble": {"oracle": {"A": 0.9}, "teacher_own": {"A": 0.9}}})
    baseline = {"student": {p: {"panel": {"mean": base["s0"][p], "exact_rate": 0.0}, "subsample": {"mean": base["s0sub"][p]}} for p in ("E_A", "E_B")},
                "teacher": {p: {"mean": base["t"][p], "subsample_mean": base["tsub"][p], "exact_rate": 0.5} for p in ("E_A", "E_B")}}
    return {"design": {"replicates": n, "updates": 2000}, "prefreeze": {"teacher_only": True, "stop": None}, "gates": {g: {"ok": True} for g in ("G1", "G4", "G5", "G6", "G7", "G8", "G9")},
            "baseline": baseline, "replicates": reps, "incomplete": [], "engineering": []}


def main():
    trials = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
    rng = random.Random(229501)
    rows_seen = Counter()
    disagreements = []
    loose_dis = []
    crashes = []
    for t in range(trials):
        n = rng.choice([3, 4])
        base, cells = scenario(rng, n)
        nc = numeric_cells(base, cells)
        study = serialize(base, nc, n)
        try:
            out = analysis.analyze(study)
        except Exception as e:  # keep every crash
            crashes.append((t, repr(e)[:200]))
            continue
        mine = S.label(base, nc, n)
        mine_loose = S.label(base, nc, n, strict_undefined=False)
        rows_seen[out["label_row"]] += 1
        cls_impl = {m: {o: out["classes"][m][o]["class"] for o in ("AB", "BA")} for m in S.MECH} if out["label_row"] > 2 else None
        cls_mine = {m: {o: S.mech_class(base, nc, n, m, o) for o in ("AB", "BA")} for m in S.MECH}
        cls_loose = {m: {o: S.mech_class(base, nc, n, m, o, strict_undefined=False) for o in ("AB", "BA")} for m in S.MECH}
        if out["label_row"] != mine or (cls_impl is not None and cls_impl != cls_mine):
            disagreements.append({"trial": t, "impl_row": out["label_row"], "auditor_row": mine, "impl_classes": cls_impl, "auditor_classes": cls_mine})
        if out["label_row"] != mine_loose or (cls_impl is not None and cls_impl != cls_loose):
            loose_dis.append({"trial": t, "impl_row": out["label_row"], "auditor_loose_row": mine_loose, "impl_classes": cls_impl, "auditor_loose_classes": cls_loose})
    print("trials", trials, "rows seen (impl):", dict(sorted(rows_seen.items())))
    print("crashes:", len(crashes), crashes[:5])
    print("disagreements vs strict reading:", len(disagreements))
    print("disagreements vs loose reading (undefined masked by a failing clause, as implemented):", len(loose_dis))
    Path(sys.argv[3] if len(sys.argv) > 3 else "/dev/null").write_text(json.dumps({"strict": disagreements[:40], "loose": loose_dis[:40], "crashes": crashes[:40]}, indent=1, default=str))


if __name__ == "__main__":
    main()
