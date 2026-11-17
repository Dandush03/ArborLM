"""Re-check auditor C: synthetic study records in the format studies/p10s2/analysis.py reads (my own serializer).
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""

import math

import rules_v2 as S

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
GATES = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9")
N_C = 6  # combined-set size in the synthetic records


def to_score(base, p, G, sub=False):
    if G in ("nan", "missing"):
        return float("nan")
    s0 = base["s0sub" if sub else "s0"][p]
    return s0 + G * (0.8 if not sub else 0.76)


def jnum(x):
    return "nan" if isinstance(x, float) and math.isnan(x) else x


def pairs(n=N_C):
    return S.c1_pairs(list(range(n)))


def comb_record(per_lang, n=N_C):
    """A combined record with constant per-item scores: per_lang = {kind: {lang: sK}, 'single': {lang: sS}}."""
    ps = pairs(n)
    out = {"n": n, "pairs_sha256": "x"}
    for kind in ("C1", "C2"):
        if kind == "C1":
            items = [{"j": j, "i": [i1, i2], "langs": [t1, t2], "scores": [per_lang["single"][t1], per_lang[kind][t2]]} for j, i1, i2, t1, t2 in ps]
        else:
            items = [{"j": i, "i": [i, i], "langs": ["A", "B"], "scores": [per_lang[kind]["A"], per_lang[kind]["B"]]} for i in range(n)]
        tested = S.tested_items(kind, ps if kind == "C1" else n)
        item_scores = [(it["scores"][0] + it["scores"][1]) / 2 for it in items]
        out[kind] = {"kind": kind, "n": n, "items": items, "mean": sum(item_scores) / n, "pass_rate": 0.0, "item_scores": item_scores,
                     "tested_sentences": tested, "tested_by_language": {a: per_lang[kind][a] for a in S.TASKS}}
    out["single"] = {"scores": {a: [per_lang["single"][a]] * n for a in S.TASKS}}
    return out


def serialize(base, ncells, n, *, gates, ensembles, combined, assembled, stage0_comb=None, ens_comb=None):
    def pn(x):
        return {"mean": jnum(x), "exact_rate": 0.0}

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
            if c.gen is not None:
                snap["gen"] = {k: jnum(x) for k, x in zip(("loss_increase", "loss_increase_first_marker"), c.gen) if x is not None}
            if combined.get((r, g, v)) is not None:
                snap["combined"] = combined[(r, g, v)]
            rec = {"label": label, "status": c.status, "train": [{"wall_seconds": 10.0}], "scores": {label: snap} if c.status == "completed" else {},
                   "extras": {"consolidation": {"rejected": c.rejected, "below_floor": c.below_floor}} if g == "MII" else {}}
            cs[label] = rec
        e = ensembles[r]
        ens = None if e is None else {"oracle": {"A": 0.9, "B": 0.8}, "teacher_own": {"A": 0.9 if e != "nan" else "nan", "B": 0.8 if e != "differ" else 0.81}}
        reps.append({"cells": cs, "assembled": assembled[r], "retrieval": {}, "routers": {}, "ensemble": ens})
    baseline = {"student": {p: {"panel": {"mean": base["s0"][p], "exact_rate": 0.0}, "subsample": {"mean": base["s0sub"][p]}} for p in ("E_A", "E_B")},
                "teacher": {p: {"mean": base["t"][p], "subsample_mean": base["tsub"][p], "exact_rate": 0.5} for p in ("E_A", "E_B")}}
    if stage0_comb is not None or ens_comb is not None:
        baseline["combined"] = {"stage0": stage0_comb, "ensemble": ens_comb}
    g = None if gates is None else {k: {"ok": v} for k, v in gates.items()}
    return {"design": {"replicates": n, "updates": 2000}, "prefreeze": {"teacher_only": True, "stop": None}, "gates": g,
            "baseline": baseline, "replicates": reps, "incomplete": [], "engineering": []}
