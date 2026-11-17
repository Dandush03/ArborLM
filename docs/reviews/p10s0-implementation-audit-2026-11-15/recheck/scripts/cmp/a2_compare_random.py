"""Compare studies.p10s0.analysis.analyze with the auditor's own rules (a1_rules_from_adr.py) over many random synthetic registries.

The registries are built by THIS script (own random generator); studies.p10s0's dataclasses (SObservation, CellData, RunData) are used only
as containers, and studies.p10s0.core only for the registry (q1_cells, wx_cells, probe_cells; cross-checked against the ADR counts first).

Usage (inside the audited worktree): uv run --locked python <this> <n_cases> <seed>
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
"""

import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import a1_rules_from_adr as R  # noqa: E402

from studies.p10s0 import analysis, core  # noqa: E402
from studies.p10s0 import classes as C  # noqa: E402

N_CASES = int(sys.argv[1]) if len(sys.argv) > 1 else 500
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 1
rng = random.Random(SEED)

# --- registry cross-check against the ADR (section 6.1) -------------------------------------------------------------
q1 = core.q1_cells(False)
q1c = core.q1_cells(True)
assert len(q1) == 230 and len(q1c) == 190
cnt = Counter((c.arm, c.celltype) for c in q1)
exp = {("A0", "2K/4K"): 20, ("A1", "2K/4K"): 20, ("A2", "2K/4K"): 20, ("A5-D", "2K/4K"): 20, ("A6", "2K/4K"): 10, ("A7", "2K/4K"): 10,
       ("A0", "8K/16K"): 20, ("A1", "8K/16K"): 20, ("A2", "8K/16K"): 20, ("A5-D", "8K/16K"): 20, ("A6", "8K/16K"): 10, ("A7", "8K/16K"): 10,
       ("A0", "8K/4K"): 10, ("A5-D", "8K/4K"): 10, ("A6", "8K/4K"): 10}
assert dict(cnt) == exp, cnt
for c in q1:
    if c.arm in ("A6", "A7"):
        assert c.seed_index == 0
    elif c.celltype == "8K/4K":
        assert c.seed_index == (0 if c.draw % 2 == 1 else 1)
cntc = Counter((c.arm, c.celltype) for c in q1c)
assert all(cntc[(a, "8K/16K")] == 10 for a in ("A0", "A1", "A2", "A5-D")) and cntc[("A6", "8K/16K")] == 10
for c in q1c:
    if c.celltype == "8K/16K" and c.arm not in ("A6", "A7"):
        assert c.seed_index == (0 if c.draw % 2 == 1 else 1)

LEARNED = ("A0", "A1", "A2", "A5-D")
ARM_CTS = {"A0": ("2K/4K", "8K/16K", "8K/4K"), "A1": ("2K/4K", "8K/16K"), "A2": ("2K/4K", "8K/16K"), "A5-D": ("2K/4K", "8K/16K", "8K/4K")}


def rand_obs(kind_p):
    """A random observation dict (auditor's field names) given a failure propensity."""
    acc = 0.97
    o = {"acc_a": acc, "acc_b": acc, "dep_a": True, "dep_b": True, "h1": acc, "h2": acc, "leak": False, "distinct": 256, "share": 5 / 512,
         "probe_facts": 256, "lm": 0.10, "stab": rng.choice([0.95, 0.9, 0.85]), "ause_a": acc, "ause_b": acc}
    if rng.random() < kind_p:
        what = rng.choice(["acc", "dep", "slot", "slot_edge", "held", "held_edge", "leak", "ause", "ause_edge", "acc_edge", "nan", "share_edge", "multi"])
        if what in ("acc", "multi"):
            o["acc_a"] = rng.choice([0.05, 0.5, 0.8])
            o["ause_a"] = min(o["ause_a"], o["acc_a"])
            o["h1"] = o["h2"] = min(o["h1"], o["acc_a"])
        if what == "acc_edge":
            o["acc_b"] = rng.choice([0.9 * 0.95, 0.9 * 0.95 - 1e-9])  # boundary against an A6 of 0.95
            o["ause_b"] = o["acc_b"]
            o["h1"] = o["h2"] = o["acc_b"]
        if what in ("dep", "multi"):
            o[rng.choice(["dep_a", "dep_b"])] = False
        if what in ("slot", "multi"):
            o["distinct"] = rng.choice([1, 3, 64])
            o["share"] = rng.choice([0.5, 0.9])
        if what == "slot_edge":
            o["distinct"] = rng.choice([127, 128])
        if what == "share_edge":
            o["share"] = rng.choice([10 / 512, 11 / 512, 0.02])
        if what == "held":
            o["h2"] = 0.5
        if what == "held_edge":
            o["h1"] = rng.choice([0.9 * acc, 0.9 * acc - 1e-9])
        if what == "leak":
            o["leak"] = True
        if what == "ause":
            o["ause_" + rng.choice("ab")] = rng.choice([0.0, 0.4 * acc, 0.9 * acc])
        if what == "ause_edge":
            o["ause_a"] = rng.choice([0.95 * acc, 0.95 * acc - 1e-9])
        if what == "nan":
            o[rng.choice(["acc_a", "ause_b", "h1"])] = math.nan
    if rng.random() < 0.03:
        o["lm"] = rng.choice([0.16, 0.5, math.nan])  # flagged against A6's 0.10
    if rng.random() < 0.05:
        o["stab"] = rng.choice([0.79, 0.80, 0.5, math.nan])
    return o


def to_sobs(o):
    return C.SObservation(acc_a=o["acc_a"], acc_b=o["acc_b"], dep_chance_a=o["dep_a"], dep_chance_b=o["dep_b"], h1=o["h1"], h2=o["h2"], leakage=o["leak"],
                          distinct_top1=o["distinct"], largest_share=o["share"], probe_facts=o["probe_facts"], lm_rise=o["lm"], address_stability=o["stab"],
                          recall_top8=math.nan, probe_accuracy=math.nan, a_use_a=o["ause_a"], a_use_b=o["ause_b"])


def a6_obs(acc_a, acc_b, lm=0.10):
    return {"acc_a": acc_a, "acc_b": acc_b, "dep_a": True, "dep_b": True, "h1": 1.0, "h2": 1.0, "leak": False, "distinct": 256, "share": 0.0,
            "probe_facts": 256, "lm": lm, "stab": 1.0, "ause_a": 0.0, "ause_b": 0.0}


def rand_p9(arm, size):
    r = rng.random()
    if r < 0.12:
        return {"available": False, "reason": "synthetic"}
    cls = rng.choice(["RELIABLE", "RELIABLE", "UNRELIABLE", "FAILS", "NOT_EVALUATED"])
    n = 8 if size == "4096" else 4
    fd = 0 if cls == "RELIABLE" else rng.randint(0, n)
    if cls == "RELIABLE" and rng.random() < 0.3:
        fd = 1
    lm = rng.random() < 0.08
    label = cls + (" (LM CAPABILITY REDUCED)" if lm else "")
    return {"available": True, "class": label, "base_class": cls, "lm_reduced": lm, "evaluated_draws": n, "failed_draws": fd, "evaluated_cells": 2 * n, "successes": 0, "draw_counts": {}, "negative_control_failed": False}


COMMITTED_P9 = {
    "A0": {"4096": {"available": True, "class": "UNRELIABLE", "base_class": "UNRELIABLE", "lm_reduced": False, "evaluated_draws": 8, "failed_draws": 6},
           "16384": {"available": True, "class": "RELIABLE", "base_class": "RELIABLE", "lm_reduced": False, "evaluated_draws": 4, "failed_draws": 0}},
    "A5-D": {"4096": {"available": True, "class": "RELIABLE", "base_class": "RELIABLE", "lm_reduced": False, "evaluated_draws": 8, "failed_draws": 0},
             "16384": {"available": True, "class": "RELIABLE", "base_class": "RELIABLE", "lm_reduced": False, "evaluated_draws": 4, "failed_draws": 0}},
    "A2": {"4096": {"available": True, "class": "FAILS", "base_class": "FAILS", "lm_reduced": False, "evaluated_draws": 8, "failed_draws": 8},
           "16384": {"available": False, "reason": "did not advance"}},
    "A1": {"4096": {"available": True, "class": "RELIABLE", "base_class": "RELIABLE", "lm_reduced": False, "evaluated_draws": 8, "failed_draws": 0},
           "16384": {"available": True, "class": "UNRELIABLE", "base_class": "UNRELIABLE", "lm_reduced": False, "evaluated_draws": 4, "failed_draws": 2}},
}


def selection_record(p9):
    return {"kind": "arm_selection", "study": "P10S0", "schema": 1, "mapping": {"not_started": False, "table_row": 3, "c4": None}, "mapping_printed": "x", "fourth_arm_printed": core.FOURTH_ARM_STRING,
            "candidates": {"arms": ["A5-D", "A1"], "excluded": {}}, "calibrated": {}, "p9ii_classes": p9, "p9ii_negative_control": {"4096": False, "16384": False}}


GATES_OK = {**{f"{g}_passed": True for g in analysis.GATES}, "g2_by_draw": {}, "harness_errors": []}


def one_case(case):
    cut3 = rng.random() < 0.25
    import os
    use_committed = os.environ.get("FORCE_COMMITTED") == "1" or rng.random() < 0.4
    p9 = COMMITTED_P9 if use_committed else {a: {s: rand_p9(a, s) for s in ("4096", "16384")} for a in LEARNED}
    # per (arm, ct) failure propensity
    prop = {(a, ct): rng.choice([0.0, 0.0, 0.03, 0.06, 0.15, 0.5, 0.95]) for a in LEARNED for ct in ARM_CTS[a]}
    # A6 per draw and cell type
    a6 = {}
    for ct in ("2K/4K", "8K/16K", "8K/4K"):
        bad = set(rng.sample(range(1, 11), rng.choice([0, 0, 0, 0, 1, 2]))) if rng.random() < 0.5 else set()
        for d in range(1, 11):
            if d in bad:
                v = (0.85, 0.95) if ct != "8K/4K" else rng.choice([(0.45, 0.6), (0.6, 0.49)])
            else:
                v = (0.95, 1.0) if ct != "8K/4K" else rng.choice([(0.6, 0.55), (0.95, 0.9)])
            a6[(ct, d)] = v
    obs = {}
    cells = {}
    for c in core.q1_cells(cut3):
        if c.arm == "A7":
            o = a6_obs(0.9, 0.9)
        elif c.arm == "A6":
            o = a6_obs(*a6[(c.celltype, c.draw)])
        else:
            o = rand_obs(prop[(c.arm, c.celltype)])
        obs[c.label] = o
        ups = c.ct.readout_updates(core.UPDATES)
        cells[c.label] = analysis.CellData({u: to_sobs(o) for u in ups}, None)
    engineering = False
    failed_tasks, missing, gates = [], [], dict(GATES_OK)
    if rng.random() < 0.05:
        lab = rng.choice(list(cells))
        del cells[lab]
        missing.append(lab)
        engineering = True
    if rng.random() < 0.03:
        gates["g6_passed"] = False
        engineering = True
    if rng.random() < 0.02:
        failed_tasks.append("train-q1:" + rng.choice(list(cells)))
        engineering = True

    # --- auditor's derivation -----------------------------------------------------------------------------------------
    mine = {"arms": {}}
    vs, vp = {}, {}
    for a in LEARNED:
        for ct in ARM_CTS[a]:
            keys = [(c.draw, c.seed_index) for c in core.q1_cells(cut3) if c.arm == a and c.celltype == ct]
            rule = "20" if len(keys) == 20 else "10"
            s0v, p9v, stabs = {}, {}, []
            for d, j in keys:
                lab = core.make_label("Q1", a, ct, d, j)
                if lab not in obs or lab in missing:
                    continue
                ref = a6[(ct, d)] + (0.10,)
                s0v[(d, j)] = R.verdict(obs[lab], ref, ct, True)
                p9v[(d, j)] = R.verdict(obs[lab], ref, ct, False)
                if s0v[(d, j)][0] != "NE":
                    stabs.append(obs[lab]["stab"])
            vs[(a, ct)], vp[(a, ct)] = s0v, p9v
            s0c, p9c_ = R.arm_class(s0v, rule), R.arm_class(p9v, rule)
            st = R.stable(stabs)
            e = {"s0": s0c, "p9": p9c_, "stable": st, "meets": s0c["cls"] == "RELIABLE" and st, "nan_stab": any(not math.isfinite(x) for x in stabs)}
            if ct in R.CORE:
                p = p9[a]["4096" if ct == "2K/4K" else "16384"]
                lab, ok, pf, pn = R.consistency(p, p9c_["draws_failed"], p9c_["draws_ev"])
                e["consistency"] = (lab, ok, pf, pn)
                e["consistent"] = ok
                e["replication"] = R.replication(p9c_["cls"], p)
            mine["arms"].setdefault(a, {})[ct] = e
    a6_ne_2k = sum(1 for d in range(1, 11) if not R.a6_usable(a6[("2K/4K", d)] + (0.1,), "2K/4K"))
    cand, q4096, also, q = R.select({a: {ct: mine["arms"][a][ct] for ct in R.CORE} for a in LEARNED})
    row = R.outcome(engineering, a6_ne_2k, cand, q4096)
    mine["row"] = row
    if row in (4, 5, 6):
        mine["cand"], mine["q4096"], mine["also"] = (cand if row == 4 else None), (q4096 if row == 5 else None), also
        if row == 5:
            mine["why"] = R.why_16384(mine["arms"][q4096]["8K/16K"])
        paired_s0 = {a: {ct: R.paired(vs[(a, ct)], vs[("A0", ct)]) for ct in R.CORE} for a in ("A1", "A2", "A5-D")}
        paired_p9 = {a: {ct: R.paired(vp[(a, ct)], vp[("A0", ct)]) for ct in R.CORE} for a in ("A1", "A2", "A5-D")}
        mine["paired_s0"], mine["paired_p9"] = paired_s0, paired_p9
        c4 = cand if row == 4 else None
        ovl = R.overload(c4, mine["arms"][c4]["8K/4K"]["s0"]["cls"] if c4 in ("A0", "A5-D") else None)
        mine["overload"] = ovl
        classes = {a: {ct: mine["arms"][a][ct]["s0"]["cls"] for ct in R.CORE} for a in LEARNED}
        repl = {(a, ct): mine["arms"][a][ct]["replication"] for a in LEARNED for ct in R.CORE}
        mine["hyp"] = R.hypotheses(classes, paired_s0, repl, row, None, ovl)

    # WX and probe cells for the auditor's candidate
    wx_kinds = None
    if row == 4 and cand in ("A5-D", "A1"):
        wxp = rng.choice([0.0, 0.0, 0.1, 0.6])
        for c in core.wx_cells(cand):
            o = rand_obs(wxp)
            obs[c.label] = o
            cells[c.label] = analysis.CellData({u: to_sobs(o) for u in c.ct.readout_updates(core.UPDATES)}, None)
        prp = rng.choice([0.0, 0.5, 1.0])
        pa6 = {d: rng.choice([(0.95, 0.95), (0.95, 0.95), (0.85, 0.95)]) for d in (11, 12, 13)}
        for c in core.probe_cells(cand):
            o = a6_obs(*pa6[c.draw]) if c.arm == "A6" else rand_obs(prp)
            obs[c.label] = o
            cells[c.label] = analysis.CellData({u: to_sobs(o) for u in c.ct.readout_updates(core.UPDATES)}, None)
        wxc, wxs = {}, {}
        for ct in R.CORE:
            v, stabs = {}, []
            for c in core.wx_cells(cand):
                if c.celltype != ct:
                    continue
                ref = a6[(ct, c.draw)] + (0.10,)
                v[(c.draw, c.seed_index)] = R.verdict(obs[c.label], ref, ct, True)
                if v[(c.draw, c.seed_index)][0] != "NE":
                    stabs.append(obs[c.label]["stab"])
            wxc[ct] = R.arm_class(v, "10")["cls"]
            wxs[ct] = R.stable(stabs)
        mine["wx"] = R.wx_label(wxc, wxs)
        pv = {}
        for c in core.probe_cells(cand):
            if c.arm == "A6":
                continue
            pv[c.draw] = R.verdict(obs[c.label], pa6[c.draw] + (0.10,), "32K/64K", True)[0]
        if any(s == "NE" for s in pv.values()):
            mine["probe"] = ("NOT_EVALUATED", None)
        else:
            mine["probe"] = ("COMPLETE", sum(1 for s in pv.values() if s == "S"))
        k = mine["probe"][1]
        mine["hyp"]["H20-L"] = "supported" if mine["wx"] == "PASSES" else ("not supported" if mine["wx"] in ("PASSES AT 4,096 ONLY", "DOES NOT PASS") else "not tested")
        mine["hyp"]["H20-S"] = "supported" if k == 3 else ("CONTRADICTED" if k == 0 and mine["probe"][0] == "COMPLETE" else "not supported")

    run = analysis.RunData(cells, selection_record(p9), failed_tasks, gates, None, cut3, {}, None, [], core.UPDATES)
    theirs = analysis.analyze(run)
    return compare(case, mine, theirs, cut3, use_committed)


DIFFS = []
COUNTS = Counter()


def note(case, what, a, b):
    DIFFS.append({"case": case, "what": what, "auditor": a, "implementation": b})


def compare(case, mine, th, cut3, committed):
    row_t = th["outcome"]["row"]
    COUNTS[f"row {mine['row']}"] += 1
    if mine["row"] != row_t:
        detail = {a: {ct: (e["s0"]["cls"], e["stable"], e.get("consistency")) for ct, e in mine["arms"][a].items()} for a in LEARNED}
        tdetail = {a: {ct: (t["s0"]["cls"], t["stable"], t.get("consistency", {}) and t["consistency"].get("label")) for ct, t in th.get("arms", {}).get(a, {}).items()} for a in LEARNED}
        note(case, "outcome row", mine["row"], {"row": row_t, "mine": detail, "theirs": tdetail, "sel": th.get("selection", {}).get("per_arm")})
        return
    if mine["row"] not in (4, 5, 6):
        return
    for a in LEARNED:
        for ct, e in mine["arms"][a].items():
            t = th["arms"][a][ct]
            COUNTS[f"class {e['s0']['cls']}"] += 1
            for key, tk in (("s0", "s0"), ("p9", "p9ii_criteria")):
                if e[key]["cls"] != t[tk]["cls"]:
                    note(case, f"{key} class {a} {ct}", e[key]["cls"], t[tk]["cls"])
                for f1, f2 in (("draws_failed", "draws_failed"), ("draws_ev", "draws_evaluated"), ("succ", "successes"), ("lm", "lm_reduced")):
                    if e[key][f1] != t[tk][f2]:
                        note(case, f"{key} {f1} {a} {ct}", e[key][f1], t[tk][f2])
            if e["stable"] != (t["stable"]["label"] == C.ADDRESS_STABLE):
                note(case, f"stable(non-finite-present={e.get('nan_stab')}) {a} {ct}", e["stable"], t["stable"])
            if e["meets"] != t["meets"]:
                note(case, f"meets(non-finite-present={e.get('nan_stab')}) {a} {ct}", e["meets"], t["meets"])
            if ct in R.CORE:
                lab, ok, pf, pn = e["consistency"]
                tc = t["consistency"]
                COUNTS[f"consistency {lab}"] += 1
                if t["s0"]["cls"] == "NOT_EVALUATED":
                    # implementation prints NOT DEFINED and consistent False; compare only the 'consistent' bit's effect (meets is False anyway)
                    COUNTS["consistency NOT DEFINED (S0 NE)"] += 1
                else:
                    tl = {C.CONSISTENT: "CONSISTENT", C.INCONSISTENT: "INCONSISTENT", C.SINGLE_STUDY: "SINGLE"}[tc["label"]]
                    if (lab, ok, pf, pn) != (tl, tc["consistent"], tc["pooled_failed"], tc["pooled_n"]):
                        note(case, f"consistency {a} {ct}", (lab, ok, pf, pn), (tl, tc["consistent"], tc["pooled_failed"], tc["pooled_n"]))
                rl = {"REPLICATES": C.REPLICATES, "DOES NOT REPLICATE": C.NOT_REPLICATE, "NOT COMPARABLE": C.NOT_COMPARABLE}[e["replication"]]
                if rl != t["replication"]:
                    note(case, f"replication {a} {ct}", e["replication"], t["replication"])
    sel = th["selection"]
    tc4 = sel["candidate"] if mine["row"] == 4 else None
    if mine.get("cand") != tc4:
        note(case, "candidate", mine.get("cand"), tc4)
    tq = sel["qualified_4096_only"] if mine["row"] == 5 else None
    if mine.get("q4096") != tq:
        note(case, "qualified 4096 only", mine.get("q4096"), tq)
    my_also = [f"ALSO QUALIFIES: {a} ({'4,096 AND 16,384' if s == 'BOTH' else '4,096 ONLY'})" for a, s in mine["also"]]
    if my_also != sel["also_qualifies"]:
        note(case, "also qualifies", my_also, sel["also_qualifies"])
    if mine["row"] == 4:
        COUNTS[f"candidate {mine['cand']}"] += 1
    if committed:
        COUNTS[f"committed-P9II row {mine['row']} cand {mine.get('cand')} q4096 {mine.get('q4096')}"] += 1
        if th["selection"].get("answer_only_suffices"):
            note(case, "ANSWER-ONLY SUFFICES printed with committed P9-II records", None, th["selection"]["answer_only_suffices"])
        for a in ("A0", "A2"):
            if mine.get("cand") == a or mine.get("q4096") == a or th["selection"]["candidate"] == a or th["selection"]["qualified_4096_only"] == a:
                note(case, f"{a} qualified with committed P9-II records", None, a)
        if (th["selection"]["candidate"] == "A1") and mine["arms"]["A1"]["8K/16K"]["p9"]["draws_failed"] != 0:
            note(case, "A1 qualified at both sizes with a failed S0 8K/16K draw under P9-II criteria", None, "A1")
    if mine["row"] == 5:
        COUNTS[f"q4096 {mine['q4096']} why {mine['why']}"] += 1
        why_t = th["outcome"]["detail"]["why_16384_missing"]
        cat = "NOT_EVALUATED" if why_t.startswith("NOT_EVALUATED") else "NOT STABLE" if why_t.startswith("not ADDRESS") else "INCONSISTENT" if "INCONSISTENT" in why_t else why_t.split(" ")[0]
        if cat == "UNRELIABLE" and "LM" in why_t:
            cat = "UNRELIABLE"
        if cat != mine["why"]:
            note(case, "why 16,384 missing", mine["why"], why_t)
    for a in ("A1", "A2", "A5-D"):
        for ct in R.CORE:
            for key, tk in (("paired_s0", "s0"), ("paired_p9", "p9ii")):
                lab, d = mine[key][a][ct]
                t = th["paired"][a][ct][tk]
                tl = {C.IMPROVES: "IMPROVES", C.HARMS: "HARMS", C.NOT_DISTINGUISHED: "ND"}[t["label"]]
                COUNTS[f"paired {lab}"] += 1
                if (lab, d) != (tl, t["d"]):
                    note(case, f"{key} {a} {ct}", (lab, d), (tl, t["d"]))
    ovl_map = {C.OVERLOAD_QUALIFIED: "QUALIFIED", C.OVERLOAD_NOT_QUALIFIED: "NOT QUALIFIED", C.OVERLOAD_NOT_EVALUATED: "NOT_EVALUATED", C.OVERLOAD_NOT_RUN: "NOT RUN — NO TARGET INJECTION", C.OVERLOAD_NO_CANDIDATE: "NO CANDIDATE"}
    if mine["overload"] != ovl_map[th["overload"]]:
        note(case, "overload", mine["overload"], th["overload"])
    for h, r in mine["hyp"].items():
        t = th["hypotheses"].get(h, {}).get("reading")
        COUNTS[f"{h.split(' ')[0]} {r}"] += 1
        if r != t:
            note(case, f"hypothesis {h}", r, t)
    if "wx" in mine:
        tl = th["record_length"]["label"].replace("RECORD-LENGTH-FREE VARIANT: ", "").replace(" (not evidence that the record length is required)", "")
        COUNTS[f"wx {mine['wx']}"] += 1
        if mine["wx"] != tl:
            note(case, "WX label", mine["wx"], th["record_length"]["label"])
        tp = th["probe"]
        COUNTS[f"probe {mine['probe']}"] += 1
        if mine["probe"][0] != tp["status"] or (mine["probe"][0] == "COMPLETE" and mine["probe"][1] != tp["successes"]):
            note(case, "probe", mine["probe"], (tp["status"], tp.get("successes")))


for i in range(N_CASES):
    one_case(i)

by_what = Counter(d["what"].split(" ")[0] + " " + d["what"].split(" ")[1] if " " in d["what"] else d["what"] for d in DIFFS)
print(json.dumps({"cases": N_CASES, "seed": SEED, "disagreements": len(DIFFS), "by_kind": by_what, "coverage": dict(sorted(COUNTS.items()))}, indent=1, default=str))
print("first disagreements:")
for d in DIFFS[:40]:
    print(json.dumps(d, default=str))
