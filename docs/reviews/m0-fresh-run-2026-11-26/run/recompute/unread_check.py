"""For every survivor lineage: (1) uncounted rows over the bound, with the entry that left them uncounted; (2) fields that
neither pooling reads, pooled the same way, where they are over the bound (descriptive; they decide nothing under the text and R-46/R-57).
Usage: python unread_check.py MY_DIR OUT_JSON"""
import json, sys, os
from fractions import Fraction as F
from collections import defaultdict
MY, OUTJ = sys.argv[1], sys.argv[2]
RUN = "/Users/daniellaloush/dandush03/ArborLM/experiments/m0_fresh_run_20261126"
IMPL = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
plan = json.load(open(f"{IMPL}/studies/m0/fresh_run/run_plan.json"))
B = F(3, 20)
rows = [json.loads(l) for l in open(f"{MY}/rows.jsonl")]
unc_over = defaultdict(list)
for r in rows:
    if not r["counted"]:
        e = F(r["excess"]["fraction"]); u = F(r["unc"]["fraction"])
        if abs(e) + u > B:
            unc_over[r["lineage"]].append((float(abs(e) + u), r["unit"], r["src"], r["rule"], r["reading"], r["level"], r["entry"]))
unread = defaultdict(list)
def note(lid, what, lv, val, n):
    if abs(val) > B:
        unread[lid].append((float(val), what, lv, n))
S = ("1", "2", "3")
# R1b mode_rate (in-sample commonest answer): its excess over chance
for lid in plan["units"]["R1b"]["outputs"][0]["id_map"]:
    for lv in range(7):
        num = F(0); den = 0
        for s in S:
            for l in open(f"{RUN}/R1b/seed{s}/{lid}.aud.jsonl"):
                x = json.loads(l)
                if x["level"] == lv and x["heuristic"] == "constant_mfk_fitted":
                    num += x["n"] * (F(repr(x["mode_rate"])) - F(repr(x["chance"]))); den += x["n"]
        if den:
            note(lid, "R1b mode_rate - chance (in-sample)", lv, num / den, den)
# M1a own/a4 answer_echoed_anywhere, own mode_insample
for s_ in ("own", "a4"):
    for lv in range(7):
        acc = defaultdict(lambda: [F(0), 0, F(0)])
        for s in S:
            raw = json.load(open(f"{RUN}/M1a/seed{s}/battery.json"))["raw"][s_]
            for lid, L in raw.items():
                r = L.get(str(lv))
                if not r:
                    continue
                a = acc[lid]; a[0] += r["N"] * F(repr(r["answer_echoed_anywhere"])); a[1] += r["N"]
                if "mode_insample" in r:
                    a[2] += r["N"] * F(repr(r["mode_insample"]))
        for lid, (x, n, m) in acc.items():
            note(lid, f"M1a {s_} answer_echoed_anywhere", lv, x / n, n)
            if s_ == "own":
                note(lid, "M1a own mode_insample", lv, m / n, n)
# C1 oracle_any_literal (a3 outputs and battery), best_generic_in_shape (battery), s5 MF_in_shape_cv recovered, a3 mf_in_shape_cv recovered
for unit in ("C1a", "C1c"):
    o = [x for x in plan["units"][unit]["outputs"] if x["form"] == "c1_a3"][0]
    for lid, ps in o["per_survivor"].items():
        for lv in range(7):
            n = 0; ol = F(0); mfin = 0
            for s in S:
                rl = json.load(open(f"{RUN}/{unit}/seed{s}/a3/run_log.json")).get(ps["run_log_key"], {})
                f, k = (ps["fallback_file"], ps["fallback_key"]) if (ps["fallback_file"] and rl.get("alias_rc", 0) != 0) else (ps["primary_file"], ps["primary_key"])
                r = json.load(open(f"{RUN}/{unit}/seed{s}/{f}"))[k][str(lv)]
                n += r["n"]; ol += r["n"] * F(repr(r["oracle_any_literal"]))
                seen = {}
                for key, v in r["S"].items():
                    sh = key.split("|", 1)[0]
                    if "mf_in_shape_cv" in v and sh not in seen:
                        seen[sh] = round(v["mf_in_shape_cv"] * v["n_shape"])
                mfin += sum(seen.values())
            note(lid, f"{unit} a3 oracle_any_literal", lv, ol / n, n)
            note(lid, f"{unit} a3 mf_in_shape_cv recovered (shapes with an S row only)", lv, F(mfin, n), n)
    o5 = [x for x in plan["units"][unit]["outputs"] if x["form"] == "c1_s5"][0]
    d = {s: json.load(open(f"{RUN}/{unit}/seed{s}/s5.json")) for s in S}
    for l, lid in o5["id_map"].items():
        for lv in range(7):
            n = 0; h = 0
            for s in S:
                r = d[s][l][str(lv)]; n += r["n"]
                for key, v in r["rules"].items():
                    if key.endswith("|MF_in_shape_cv"):
                        h += round(v["rate_in_shape"] * v["n_shape"])
            note(lid, f"{unit} s5 MF_in_shape_cv recovered and summed", lv, F(h, n), n)
d = {s: json.load(open(f"{RUN}/C1b/seed{s}/battery.json")) for s in S}
for lid in plan["units"]["C1b"]["outputs"][0]["id_map"]:
    for lv in range(7):
        n = 0; ol = F(0); bg = 0
        for s in S:
            r = d[s][lid][str(lv)]; n += r["n"]; ol += r["n"] * F(repr(r["oracle_any_literal"]))
            for sh, v in r.get("best_generic_in_shape", {}).items():
                bg += round(v["rate"] * r["shapes"][sh])
        note(lid, "C1b oracle_any_literal", lv, ol / n, n)
        note(lid, "C1b best_generic_in_shape recovered (chosen and scored on the same items)", lv, F(bg, n), n)
out = {"uncounted_over": unc_over, "unread_over": unread}
json.dump(out, open(OUTJ, "w"), indent=1, default=str)
per = json.load(open(f"{MY}/per_lineage.json"))
for lid in sorted(per):
    a = sorted(unc_over.get(lid, []), reverse=True); b = sorted(unread.get(lid, []), reverse=True)
    if a or b:
        print(f"{lid} [{'DROP' if per[lid]['dropped'] else 'keep'}] uncounted-over={len(a)} unread-over={len(b)}")
        for x in a[:4]:
            print("    U", f"{x[0]:.4f}", x[1:])
        for x in b[:4]:
            print("    R", f"{x[0]:.4f}", x[1:])
