"""v2: attempt 1 wrote two expectations as "16", "2", "20"; the script writes every fraction as p/q ("16/1"); the values were equal, the format was mine. Recheck cases (R-56, R-57, hash checks): expected values written by hand. usage: python3 -I check_recheck.py RUNS_DIR"""
import json, sys
from fractions import Fraction as F
R = sys.argv[1]
res = []
def L(n, f): return json.load(open(f"{R}/{n}/{f}"))
def fr(x): return None if x is None else F(x["fraction"])
def case(cid, desc, exp, got): res.append((cid, desc, exp, got, "PASS" if exp == got else "FAIL"))
def row(T, unit, lid, lv, rule, reading, source=None):
    x = [r for r in T if r["unit"] == unit and r["lineage"] == lid and r["level"] == lv and r["rule"] == rule and r["reading"] == reading and (source is None or r["source"] == source)]
    return x[0] if len(x) == 1 else None
def rc(cid, desc, r, **kw):
    if r is None: case(cid, desc, "one row", "none or several"); return
    got = {}
    for k in kw:
        got[k] = {"excess": lambda: fr(r["excess"]), "margin": lambda: fr(r["abs_excess_plus_uncertainty"]), "over": lambda: r["over_bound"],
                  "counted": lambda: r["counted"], "stripped": lambda: r["bracket_stripped"]}[k]()
    case(cid, desc, {k: str(v) for k, v in kw.items()}, {k: str(v) for k, v in got.items()})
U4, U4b = F(1, 20000), F(1, 10000)
# ---- old echo fixture: the one expectation R-56 changes
T = L("old_echo", "pooled_table.json"); Dp = {d["lineage"] for d in L("old_echo", "dropped.json")}
rc("a0-written", "old echo fixture: written name [max/max] still 2/15, kept", row(T, "M1a", "M1.ratio_share_r3", 5, "im:echo_best_position[max/max]", "vs_chance", "own"), excess=F(2, 15), over=False, stripped=False)
rc("a0-stripped", "old echo fixture: stripped name 1/5 vs chance, dropped", row(T, "M1a", "M1.ratio_share_r3", 5, "im:echo_best_position", "vs_chance", "own"), excess=F(1, 5), margin=F(1, 5) + U4, over=True, stripped=True)
case("a0-drop", "old echo fixture: M1.ratio_share_r3 now dropped (was kept under v1; changed by R-56)", True, "M1.ratio_share_r3" in Dp)
# ---- r56 fixture
T = L("new_r56", "pooled_table.json"); Dp = {d["lineage"] for d in L("new_r56", "dropped.json")}; EX = L("new_r56", "report_extras.json")
rc("a1", "(a) written [max/max]: 0.2*200/300 = 2/15 kept", row(T, "M1a", "M1.e56_echo_r3", 6, "im:echo_best_position[max/max]", "vs_chance", "own"), excess=F(2, 15), over=False)
rc("a2", "(a) written [max/last]: 1/15 kept", row(T, "M1a", "M1.e56_echo_r3", 6, "im:echo_best_position[max/last]", "vs_chance", "own"), excess=F(1, 15), over=False)
rc("a3", "(a) stripped vs chance 1/5 + 1/20000: dropped", row(T, "M1a", "M1.e56_echo_r3", 6, "im:echo_best_position", "vs_chance", "own"), excess=F(1, 5), margin=F(1, 5) + U4, over=True, counted=True, stripped=True)
rc("a4", "(a) stripped vs base 0.05: 3/20 + 1/10000: dropped", row(T, "M1a", "M1.e56_echo_r3", 6, "im:echo_best_position", "vs_base", "own"), excess=F(3, 20), margin=F(3, 20) + U4b, over=True)
case("a5", "(a) e56_echo dropped and listed as differing only under the second reading", [True, True, False],
     [ "M1.e56_echo_r3" in Dp, any(x["lineage"] == "M1.e56_echo_r3" for x in EX["m1a_bracket_second_reading_lineages_whose_outcome_differs"]),
       next((x["dropped_without_it"] for x in EX["m1a_bracket_second_reading_lineages_whose_outcome_differs"] if x["lineage"] == "M1.e56_echo_r3"), None)])
rc("b1", "(b) stripped exactly 3/20 (0.1499, 0.1500, 0.1501), written 4 dp: 3/20 + 1/20000 > 0.15, dropped (point 7)", row(T, "M1a", "M1.e56_drop_r3", 6, "im:echo_best_position", "vs_chance", "own"), excess=F(3, 20), margin=F(3, 20) + U4, over=True)
rc("b1w", "(b) written [a] (0.1499 and 0.1501 of 300 items) 1/10, kept", row(T, "M1a", "M1.e56_drop_r3", 6, "im:echo_best_position[a]", "vs_chance", "own"), excess=F(1, 10), over=False)
rc("b2", "(b) stripped 281/1875 (0.1498, 0.1499, 0.1499): + 1/20000 = 0.14991..., kept", row(T, "M1a", "M1.e56_keep_r3", 6, "im:echo_best_position", "vs_chance", "own"), excess=F(281, 1875), margin=F(281, 1875) + U4, over=False)
rc("b2b", "(b) same vs base 0: + 1/10000 = 0.14996..., kept", row(T, "M1a", "M1.e56_keep_r3", 6, "im:echo_best_position", "vs_base", "own"), excess=F(281, 1875), margin=F(281, 1875) + U4b, over=False)
rc("b3", "(b) stripped 1501/10000 (0.1500, 0.1501, 0.1502): dropped", row(T, "M1a", "M1.e56_above_r3", 6, "im:echo_best_position", "vs_chance", "own"), excess=F(1501, 10000), over=True)
case("b4", "(b) drops: drop_r3 yes, keep_r3 no, above_r3 yes", [True, False, True], ["M1.e56_drop_r3" in Dp, "M1.e56_keep_r3" in Dp, "M1.e56_above_r3" in Dp])
rc("c1", "(c) stripped im:largest_share on stem ratio_share (M1.ratio_share_r2): an entry, uncounted", row(T, "M1a", "M1.ratio_share_r2", 6, "im:largest_share", "vs_chance", "own"), counted=False, stripped=True)
rc("c2", "(c) written im:largest_share[a] on ratio_share_r2: not an entry, counted, 2/15 kept", row(T, "M1a", "M1.ratio_share_r2", 6, "im:largest_share[a]", "vs_chance", "own"), counted=True, excess=F(2, 15), over=False)
rc("c3", "(c) stripped im:largest_share on another stem: counted, 1/5, dropped", row(T, "M1a", "M1.e56_noentry_r3", 6, "im:largest_share", "vs_chance", "own"), counted=True, excess=F(1, 5), over=True)
case("c4", "(c) ratio_share_r2 kept, e56_noentry dropped", [False, True], ["M1.ratio_share_r2" in Dp, "M1.e56_noentry_r3" in Dp])
main_drop = {d["lineage"] for d in L("new_main", "dropped.json")}
case("r56-all", "r56 drops = main drops + e56_echo, e56_drop, e56_above, e56_noentry", sorted(main_drop | {"M1.e56_echo_r3", "M1.e56_drop_r3", "M1.e56_above_r3", "M1.e56_noentry_r3"}), sorted(Dp))
case("x1", "no bracket-stripped row outside M1a", 0, len([r for r in T if r["bracket_stripped"] and r["unit"] != "M1a"]))
case("x2", "dry_run_exclusions copied to the extras", [], EX.get("dry_run_exclusions"))
# ---- (f) report-only in-shape fields changed: no decision changes, extras carry the changed values
for f in ["pooled_table.json", "dropped.json", "per_lineage.json"]:
    case("f-" + f, f"(f) {f} identical with the in-shape report-only fields changed", True, L("new_main", f) == L("new_shapes_alt", f))
ea, eb = L("new_main", "report_extras.json"), L("new_shapes_alt", "report_extras.json")
case("f-extras-other", "(f) every other extras key identical", True, {k: v for k, v in ea.items() if k != "rates_within_one_shape_reported_only"} == {k: v for k, v in eb.items() if k != "rates_within_one_shape_reported_only"})
sr = eb["rates_within_one_shape_reported_only"]
def find(unit, source, lid, lv, shape, rule):
    return next((x["by_seed"] for x in sr if (x["unit"], x["source"], x["lineage"], x["level"], x["shape"], x["rule"]) == (unit, source, lid, lv, shape, rule)), None)
case("f-a3", "(f) a3 S row rate_in_shape 0.777 and mf_in_shape_cv 0.111 reported", {"rate_in_shape": "777/1000", "mf_in_shape_cv": "111/1000", "n_shape": "16/1"},
     {k: (find("C1a", "a3", "C1.c_err", 0, "A", "S.base") or {}).get("1", {}).get(k) for k in ("rate_in_shape", "mf_in_shape_cv", "n_shape")})
case("f-bat", "(f) battery S row rate 0.555 reported", "111/200", (find("C1b", "battery", "C1.c_err", 0, "A", "S.base") or {}).get("1", {}).get("rate"))
case("f-s5", "(f) s5 MF_in_shape_cv 0.333 reported", "333/1000", (find("C1a", "s5", "C1.c_err", 0, "A", "MF_in_shape_cv") or {}).get("1", {}).get("rate_in_shape"))
case("f-r2", "(f) R2 per-shape counts reported (g_sd removals=1, SDR rule, seed 1): k 2, n 20", ["2/1", "20/1"],
     [(find("R2b", "f_rules", "R2.g_sd", 2, "removals=1", "[a3] removal by deleting the minimum and keeping the order of the rest") or {}).get("1", {}).get(k) for k in ("k", "n")])
case("f-bmsh", "(f) battery MF_shape_cv per shape reported (c_msh L4 shape A)", "3/8", (find("C1b", "battery", "C1.c_msh", 4, "A", "MF_shape_cv") or {}).get("1", {}).get("rate_in_shape"))
for r in res: print(f"{r[4]}  {r[0]:14s} {r[1]}\n          expected {r[2]}\n          got      {r[3]}")
print(f"\nCASES {len(res)}  PASS {sum(r[4] == 'PASS' for r in res)}  FAIL {sum(r[4] == 'FAIL' for r in res)}")
