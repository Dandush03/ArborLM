"""R6 (auditor; v2: hypothesis differences classified by cause; v1 output kept as r6_classes_differential_v1_coarse_classifier.txt), Opus 5.5, re-check): old (3d779e1, imported as oldp9ii) against HEAD analysis.analyze_study on N random in-memory registries
(Stage 1 with random successes, NOT_EVALUATED draws, LM flags and A2 supervision clauses; Stage 2 COMPLETE / INCOMPLETE / NOT RUN — BUDGET /
NOT RUN — NO ARM PASSED; optional Stage 3), and a count of exactly which outputs differ. The intended differences of the fix are: hypotheses
B-G in row 3 without a COMPLETE Stage 2 (NOT TESTED AT 16,384), carry-forward from a Stage 2 that is not COMPLETE (none), the Stage 3 status
when Stage 2 did not run for budget or is INCOMPLETE, and SUPERVISION-DEPENDENT's denominator (evaluated cells only). Anything else is a finding.

usage: r6_classes_differential.py OLD_PKG_PARENT N SEED
"""
import json
import random
import sys
from collections import Counter

sys.path.insert(0, sys.argv[1])
import oldp9ii.analysis as OA  # noqa: E402
import oldp9ii.classes as OC  # noqa: E402
from studies.p9ii import analysis as NA  # noqa: E402
from studies.p9ii import classes as NC  # noqa: E402
from studies.p9ii import core  # noqa: E402

N, rng = int(sys.argv[2]), random.Random(int(sys.argv[3]))
GOOD = dict(acc_a=0.98, acc_b=0.98, dep_chance_a=True, dep_chance_b=True, h1=0.97, h2=0.97, leakage=False, distinct_top1=250, largest_share=0.008, probe_facts=256, lm_rise=0.13)
BAD = dict(GOOD, acc_a=0.05, acc_b=0.05, h1=0.05, h2=0.05, distinct_top1=3, largest_share=0.9)


def stage_data(P, stage, cells_list, outcome_of, ne_draws, sup):
    expected = {}
    cells = {}
    for c in cells_list:
        expected.setdefault(c.arm, []).append((c.draw, c.seed_index))
        o = dict(GOOD, acc_a=0.5, acc_b=0.5) if (c.arm == "A6" and c.draw in ne_draws) else (dict(GOOD, acc_a=1.0, acc_b=1.0, lm_rise=0.14) if c.arm == "A6" else (dict(GOOD) if c.arm == "A7" else (dict(GOOD) if outcome_of(c) else dict(BAD))))
        obs = {u: P[1].Observation(**o) for u in core.stage_readouts(stage)}
        summary = None
        if c.arm in core.LEARNED_ARMS:
            cat = P[1].Category(P[1].COLLAPSED_RECOVERED if o["distinct_top1"] > 100 else P[1].COLLAPSED_NOT_RECOVERED, 64, 1024 if o["distinct_top1"] > 100 else None, 64, None)
            sd, sc = (sup.get((c.draw, c.seed_index), (False, False)) if c.arm == "A2" else (None, None))
            summary = P[1].TrainingSummary(cat, True, 0.001, 2048 if o["distinct_top1"] > 100 else None, True if o["distinct_top1"] > 100 else None, sd, sc, None, 1.0 if c.arm == "A2" else None, core.stage_updates(stage), ((64, 1.0), (2048, 2.0)), 2048 if c.arm == "A2" else None)
        cells[(c.arm, c.draw, c.seed_index)] = P[0].CellData(obs, summary)
    return P[0].StageData(stage, expected, cells)


def run(P, spec):
    s1 = stage_data(P, 1, core.stage1_cells(), spec["f1"], spec["ne1"], spec["sup"])
    s2 = stage_data(P, 2, core.stage2_cells(spec["adv"]), spec["f2"], set(), {}) if spec["s2"] in ("COMPLETE", "INCOMPLETE") else None
    if s2 is not None and spec["s2"] == "INCOMPLETE":
        k = next(iter(s2.cells))
        del s2.cells[k]
    not_run = None if s2 is not None else spec["s2"]
    s3 = stage_data(P, 3, core.stage3_cells(spec["sel"]), lambda c: True, set(), {}) if spec["s3"] else None
    return P[0].analyze_study(s1, s2, s3, stage2_not_run=not_run, stage3_selected=spec["sel"] if spec["s3"] else None, gates={"g1_passed": True, "g2_passed": True, "g4_passed": True, "g5_passed": True, "g6_passed": True, "g4_defects": []})


diffs = Counter()
examples = {}
expected_kinds = {"hypotheses", "carried_forward", "stage3_status", "supervision_dependent"}
for it in range(N):
    p = {a: rng.choice([0.0, 0.3, 0.9, 1.0]) for a in core.LEARNED_ARMS}
    f1 = lambda c, p=p, salt=rng.random(): random.Random(hash((c.label, salt))).random() < p[c.arm]
    ne1 = set(rng.sample(range(1, 9), rng.choice([0, 0, 0, 1])))
    sup = {(d, j): (False, rng.random() < 0.6) for d in range(1, 9) for j in (0, 1)}
    adv = rng.choice([[], ["A5-C"], ["A4"], ["A2"], ["A5-C", "A5-D"], ["A5-D", "A4"], ["A2", "A1"]])
    s2 = rng.choice(["COMPLETE", "INCOMPLETE", "NOT RUN — BUDGET", "NOT RUN — NO ARM PASSED"])
    p2 = {a: rng.choice([0.0, 0.9, 1.0]) for a in core.LEARNED_ARMS}
    f2 = lambda c, p2=p2, salt=rng.random(): random.Random(hash((c.label, salt))).random() < p2[c.arm]
    sel = rng.choice(["A0", "A5-C", "A1"])
    spec = {"f1": f1, "ne1": ne1, "sup": sup, "adv": adv, "s2": s2, "f2": f2, "sel": sel, "s3": s2 == "COMPLETE" and rng.random() < 0.5}
    o, n = run((OA, OC), spec), run((NA, NC), spec)
    kinds = set()
    if o["outcome"]["outcome"] != n["outcome"]["outcome"] or o["outcome"]["row"] != n["outcome"]["row"] or o["outcome"]["arm"] != n["outcome"]["arm"]:
        kinds.add("OUTCOME")
    if {k: v["reading"] for k, v in o["hypotheses"].items()} != {k: v["reading"] for k, v in n["hypotheses"].items()}:
        kinds.add("hypotheses")
        row3 = n["outcome"]["row"] == 3 and n["stage2"]["status"] != "COMPLETE"
        changed = {k for k in o["hypotheses"] if o["hypotheses"][k]["reading"] != n["hypotheses"][k]["reading"]}
        supdep_changed = any("supervision_dependent" in (o.get(st) or {}).get("arms", {}).get("A2", {}) and o[st]["arms"]["A2"]["supervision_dependent"]["label"] != n[st]["arms"]["A2"]["supervision_dependent"]["label"] for st in ("stage1", "stage2"))
        if row3 and all(n["hypotheses"][k]["reading"] == NC.NOT_TESTED_16K for k in ("H19-B", "H19-C", "H19-D", "H19-F", "H19-G")):
            kinds.add("hypotheses_row3_not_tested")
        elif changed == {"H19-C"} and supdep_changed:
            kinds.add("hypotheses_H19C_follows_supervision_dependent")
        else:
            kinds.add("hypotheses_UNINTENDED")
    if o["carried_forward"]["arm"] != n["carried_forward"]["arm"]:
        kinds.add("carried_forward")
        if n["stage2"]["status"] == "COMPLETE":
            kinds.add("carried_UNINTENDED")
    if o["stage3"]["status"] != n["stage3"]["status"]:
        kinds.add("stage3_status")
    for st in ("stage1", "stage2"):
        oa, na = (o.get(st) or {}).get("arms", {}), (n.get(st) or {}).get("arms", {})
        for arm in oa:
            if oa[arm]["class"] != na[arm]["class"] or oa[arm].get("paired_against_a0") != na[arm].get("paired_against_a0"):
                kinds.add("CLASS_OR_PAIRED")
            if "supervision_dependent" in oa[arm] and oa[arm]["supervision_dependent"] != na[arm]["supervision_dependent"]:
                kinds.add("supervision_dependent")
                if not ne1:
                    kinds.add("supdep_UNINTENDED")
            if oa[arm]["draw_sensitivity"]["table"] != na[arm]["draw_sensitivity"]["table"]:
                kinds.add("DRAW_TABLE")
    for k in kinds:
        diffs[k] += 1
        examples.setdefault(k, {"old": {k2: str(v)[:300] for k2, v in o["outcome"].items()}, "new": {k2: str(v)[:300] for k2, v in n["outcome"].items()}, "s2": s2, "ne1": sorted(ne1)})
summary = {"registries": N, "differences_by_output": dict(diffs), "unintended": {k: v for k, v in diffs.items() if k.isupper() or "UNINTENDED" in k}, "examples": examples}
print(json.dumps(summary, indent=1))
