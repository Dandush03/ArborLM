# ruff: noqa
"""Summarise audit_main.json: solver disagreements, capacity vs 1,800 core / 1,000 reserve, and shortcut findings."""
import json
import sys

r = json.load(open(sys.argv[1]))
what = sys.argv[2] if len(sys.argv) > 2 else "all"
CORE = {"1", "2", "3", "4", "5"}

if what in ("all", "solver"):
    print("== solver key check (first S items per level)")
    tot = bad = err = 0
    for lid, rec in sorted(r["lineages"].items()):
        if not rec["new"]:
            continue
        for lv, d in rec["levels"].items():
            tot += d["solver_checked"]; bad += d["solver_disagree_n"]; err += d["solver_error_n"]
            if d["solver_disagree_n"] or d["solver_error_n"]:
                print(lid, lv, d["solver_disagree_n"], d["solver_error_n"], d["solver_disagree"][:2], d["solver_error"][:2])
    print(f"checked={tot} disagree={bad} error={err}")

if what in ("all", "capacity"):
    print("== capacity: distinct structured forms in N draws (threshold 1800 core, 1000 reserve)")
    for lid, rec in sorted(r["lineages"].items()):
        row = []
        fail = []
        for lv in map(str, range(7)):
            d = rec["levels"][lv]
            thr = 1800 if lv in CORE else 1000
            v = d["distinct_structured"]
            of = d.get("distinct_order_free")
            row.append(f"L{lv}:{v}" + (f"/{of}" if of is not None else ""))
            if v < thr or (of is not None and of < thr):
                fail.append(f"L{lv}({v}{'/' + str(of) if of is not None else ''}<{thr})")
        print(f"{'NEW' if rec['new'] else 'OLD'} {lid}: {' '.join(row)}  {'BELOW: ' + ', '.join(fail) if fail else ''}")

if what in ("all", "shortcuts"):
    print("== shortcuts: per lineage, worst level for each heuristic (acc vs chance / mode rate)")
    for lid, rec in sorted(r["lineages"].items()):
        if not rec["new"]:
            continue
        lv_mode = max(rec["levels"].items(), key=lambda kv: kv[1]["mode_rate"] - kv[1]["chance"])
        print(f"\n## {lid}  worst mode rate L{lv_mode[0]} = {lv_mode[1]['mode_rate']} (answer {lv_mode[1]['mode_answer']!r}, chance {lv_mode[1]['chance']}); answer-token-in-question max = {max(d['answer_token_in_question'] for d in rec['levels'].values())}")
        # per shape worst mode
        worst_shape = []
        for lv, d in rec["levels"].items():
            for sh, e in d["shapes"].items():
                worst_shape.append((e["mode_rate"] - e["chance"], lv, sh, e))
        worst_shape.sort(reverse=True)
        if worst_shape and len(rec["levels"]["3"]["shapes"]) > 1:
            g, lv, sh, e = worst_shape[0]
            print(f"   worst per-shape mode: L{lv} [{sh}] {e['mode_rate']} answer {e['mode_answer']!r} (n={e['n']}, chance {e['chance']})")
        names = sorted({n for d in rec["levels"].values() for n in d["heuristics"]})
        for name in names:
            vals = [(lv, d["heuristics"][name]) for lv, d in rec["levels"].items() if name in d["heuristics"]]
            if not vals:
                continue
            if "two_sided" in vals[0][1]:
                wlv, w = max(vals, key=lambda kv: abs(kv[1]["acc"] - 0.5))
                dirs = sorted({v["direction"] for _, v in vals})
                per = " ".join(f"L{lv}:{v['acc']:.3f}" for lv, v in vals)
                print(f"   [yn] {name}: raw acc per level {per}; most extreme L{wlv} acc={w['acc']} ci={w['ci95']} n={w['n']} -> {w['direction']}")
            else:
                wlv, w = max(vals, key=lambda kv: kv[1]["acc"] - kv[1]["chance"])
                per = " ".join(f"L{lv}:{v['acc']:.3f}" for lv, v in vals)
                print(f"   {name}: {per}  (max L{wlv} {w['acc']} ci={w['ci95']} n={w['n']})")
