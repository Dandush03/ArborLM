"""Auditor's case table: expected values written by hand from the approved text (stage 1S points 6 to 8), compared with pool_fresh.py's output.
usage: python3 -I check_cases.py RUN_OUT_DIR  -> prints one line per case: id, expected, got, PASS/FAIL"""
import json, sys
from fractions import Fraction as F

O = sys.argv[1]
T = json.load(open(f"{O}/pooled_table.json"))
PL = json.load(open(f"{O}/per_lineage.json"))
EX = json.load(open(f"{O}/report_extras.json"))
DROPPED = {d["lineage"] for d in json.load(open(f"{O}/dropped.json"))}
res = []
def fr(x): return None if x is None else F(x["fraction"])
def rows(unit, lid, lv=None, rule=None, reading=None, shape="ANY", source=None):
    return [r for r in T if r["unit"] == unit and r["lineage"] == lid and (lv is None or r["level"] == lv) and (rule is None or r["rule"] == rule)
            and (reading is None or r["reading"] == reading) and (shape == "ANY" or r["shape"] == shape) and (source is None or r["source"] == source)]
def one(*a, **k):
    x = rows(*a, **k)
    return x[0] if len(x) == 1 else {"_count": len(x)}
def case(cid, desc, expected, got):
    res.append((cid, desc, expected, got, "PASS" if expected == got else "FAIL"))
def rowcase(cid, desc, r, excess=None, counted=None, over=None, items=None, margin=None):
    exp, got = {}, {}
    if "_count" in r:
        case(cid, desc, "one row", f"{r['_count']} rows"); return
    if excess is not None: exp["excess"] = excess; got["excess"] = fr(r["excess"])
    if margin is not None: exp["margin"] = margin; got["margin"] = fr(r["abs_excess_plus_uncertainty"])
    if counted is not None: exp["counted"] = counted; got["counted"] = r["counted"]
    if over is not None: exp["over"] = over; got["over"] = r["over_bound"]
    if items is not None: exp["items"] = items; got["items"] = r["items"]
    case(cid, desc, {k: str(v) for k, v in exp.items()}, {k: str(v) for k, v in got.items()})
def drop(cid, lid, expected):
    case(cid, f"{lid} dropped?", expected, lid in DROPPED)

# ---------------- R2 (counts: exact fractions, no rounding uncertainty)
rowcase("R2-1", "open rule exactly at 0.15 (18/120): kept", one("R2a", "R2.a_open", 2, "[impl] x", "k_over_n"), excess=F(3, 20), margin=F(3, 20), over=False, counted=True, items=120)
drop("R2-1d", "R2.a_open", False)
rowcase("R2-2", "open rule just above (19/120): dropped", one("R2a", "R2.b_open", 2, "[impl] x", "k_over_n"), excess=F(19, 120), over=True)
drop("R2-2d", "R2.b_open", True)
rowcase("R2-3", "yes/no 78/120 vs 1/2: excess +0.15 exactly, kept", one("R2a", "R2.c_yn", 2, "[mine] yn hi", "k_over_napp"), excess=F(3, 20), over=False)
rowcase("R2-4", "yes/no 42/120 vs 1/2: excess -0.15 exactly, kept", one("R2a", "R2.c_yn", 2, "[mine] yn lo", "k_over_napp"), excess=F(-3, 20), over=False)
drop("R2-4d", "R2.c_yn", False)
rowcase("R2-5", "yes/no 41/120: excess -19/120 just below -0.15, dropped", one("R2a", "R2.d_yn", 2, "[mine] yn lo2", "k_over_napp"), excess=F(-19, 120), over=True)
drop("R2-5d", "R2.d_yn", True)
rowcase("R2-6", "rule named in seed 2 only (18 of 40): no hit and 40 items for seeds 1, 3 -> 18/120, kept", one("R2a", "R2.e_oneseed", 2, "[impl] once", "k_over_n"), excess=F(3, 20), items=120, over=False)
drop("R2-6d", "R2.e_oneseed", False)
rowcase("R2-7a", "[cond] k/n = 15/120 below the bound", one("R2b", "R2.f_cond", 2, "[mine] [cond] foo", "k_over_n"), excess=F(1, 8), over=False)
rowcase("R2-7b", "[cond] k/napp = 15/60 above: the larger decides", one("R2b", "R2.f_cond", 2, "[mine] [cond] foo", "k_over_napp"), excess=F(1, 4), over=True)
drop("R2-7d", "R2.f_cond", True)
SDR = "[a3] removal by deleting the minimum and keeping the order of the rest"
rowcase("R2-8a", "shape-dependent rule, removals=0 (artefact): uncounted", one("R2b", "R2.g_sd", 2, SDR, "k_over_n", shape="removals=0"), counted=False, over=False)
rowcase("R2-8b", "shape-dependent rule, removals=1 counted on its own 20 items: 6/60", one("R2b", "R2.g_sd", 2, SDR, "k_over_n", shape="removals=1"), excess=F(1, 10), counted=True, over=False, items=60)
drop("R2-8d", "R2.g_sd (summed over shapes it would be 66/120 = 0.55)", False) if False else drop("R2-8d", "R2.g_sd", False)
rowcase("R2-9", "shape-dependent rule, removals=1 12/60 = 0.2 (summed over shapes 12/120 = 0.1): dropped", one("R2b", "R2.h_sd", 2, SDR, "k_over_n", shape="removals=1"), excess=F(1, 5), over=True)
drop("R2-9d", "R2.h_sd", True)
rowcase("R2-10", "shape-dependent rule whose counts are given over shapes together (shape '-'): counts on that figure, 24/120", one("R2b", "R2.i_sdsum", 2, SDR, "k_over_n"), excess=F(1, 5), counted=True, over=True)
drop("R2-10d", "R2.i_sdsum", True)
rowcase("R2-11a", "klass order 4: '[a3] rules in reverse order' at level 0 artefact", one("R2a", "R2.j_klass", 0, "[a3] rules in reverse order", "k_over_n"), counted=False)
rowcase("R2-11b", "klass order 5: same name at level 1 is P", one("R2a", "R2.j_klass", 1, "[a3] rules in reverse order", "k_over_n"), counted=False)
rowcase("R2-11c", "klass order 1: name contains '(P'", one("R2a", "R2.j_klass", 1, "[mine] alpha (P) beta", "k_over_n"), counted=False)
rowcase("R2-11d", "klass order 7: name contains 'letter pairs' (partial)", one("R2a", "R2.j_klass", 1, "[impl] uses letter pairs here", "k_over_n"), counted=False)
rowcase("R2-11e", "klass order 4: '[a3] only the first rule' at level 0 artefact", one("R2a", "R2.j_klass", 0, "[a3] only the first rule", "k_over_n"), counted=False)
drop("R2-11d2", "R2.j_klass", False)
rowcase("R2-12", "'[a3] only the first rule' at level 1: cue, counted", one("R2a", "R2.k_klass2", 1, "[a3] only the first rule", "k_over_n"), counted=True, over=True)
drop("R2-12d", "R2.k_klass2", True)
rowcase("R2-13", "construct counts", one("R2a", "R2.l_construct", 1, "[mine] t mod 10 applications", "k_over_n"), counted=True, over=True)
drop("R2-13d", "R2.l_construct", True)
NEWP = "[NEW] (P) misread: each distinct value counted once (the wording now excludes it)"
rowcase("R2-14a", "[NEW] (P) entry for its own lineage (count_divisible): uncounted", one("R2b", "R2.count_divisible", 3, NEWP, "k_over_n"), counted=False)
rowcase("R2-14b", "same [NEW] name for another lineage: counted", one("R2b", "R2.m_new", 3, NEWP, "k_over_n"), counted=True, over=True)
drop("R2-14d1", "R2.count_divisible", False); drop("R2-14d2", "R2.m_new", True)
case("R2-15", "non-survivor lineage R2.zz_not not read", 0, len([r for r in T if r["lineage"] == "R2.zz_not"]))
# ---------------- R1
U4 = F(1, 20000)
rowcase("R1-1", "amendment-list rule on its own lineage (alpha): uncounted", one("R1a", "R1.alpha_r4", 3, "my_rule", "eff"), excess=F(3, 10), counted=False, over=False)
rowcase("R1-2", "same rule, on the amendment list for alpha only, scored for beta: counts", one("R1a", "R1.beta_r5", 3, "my_rule", "eff"), excess=F(3, 10), counted=True, over=True)
drop("R1-2d1", "R1.alpha_r4", False); drop("R1-2d2", "R1.beta_r5", True)
ex = {(e["lineage"], e["rule"]): e for e in EX["r1_exact_rows"]}
case("R1-3", "exact rule that is an entry (M abstain_as_no on alpha): listed, set aside, not counted",
     {"listed": True, "set_aside": True, "counted": False}, {"listed": ("R1.alpha_r4", "abstain_as_no") in ex, "set_aside": ex.get(("R1.alpha_r4", "abstain_as_no"), {}).get("set_aside"), "counted": ex.get(("R1.alpha_r4", "abstain_as_no"), {}).get("counted")})
case("R1-4", "exact rule not an entry (eps exact_x): listed, counts, drops", {"listed": True, "set_aside": False, "counted": True, "dropped": True},
     {"listed": ("R1.eps_r4", "exact_x") in ex, "set_aside": ex.get(("R1.eps_r4", "exact_x"), {}).get("set_aside"), "counted": ex.get(("R1.eps_r4", "exact_x"), {}).get("counted"), "dropped": "R1.eps_r4" in DROPPED})
rowcase("R1-5", "eff written 0.1500 (4 dp): + 0.00005 > 0.15, dropped", one("R1a", "R1.zeta_r4", 1, "z_rule", "eff"), excess=F(3, 20), margin=F(3, 20) + U4, over=True)
drop("R1-5d", "R1.zeta_r4", True)
rowcase("R1-6", "eff written 0.1499: 0.14995, kept", one("R1a", "R1.compass_turns", 1, "c_ok", "eff"), margin=F(1499, 10000) + U4, over=False)
rowcase("R1-7", "eff -0.1501: just below -0.15, dropped", one("R1a", "R1.eta_r4", 5, "e_neg", "eff"), excess=F(-1501, 10000), over=True)
rowcase("R1-7b", "anti 0.1499 read as an excess of its own, kept", one("R1a", "R1.eta_r4", 5, "e_neg", "anti"), excess=F(1499, 10000), over=False)
drop("R1-7d", "R1.eta_r4", True)
rowcase("R1-8", "rule named in seed 1 only (eff 0.30, n 100): seeds 2, 3 count 100 items at chance (eff 0) -> 0.10", one("R1a", "R1.theta_r4", 4, "one_seed", "eff"), excess=F(1, 10), items=300, over=False)
drop("R1-8d", "R1.theta_r4", False)
rowcase("R1-9", "row item count 40 (plan 100) in seed 1: (0.3*40+0.1*100+0.1*100)/240 = 2/15, kept", one("R1a", "R1.iota_r4", 2, "small_n", "eff"), excess=F(2, 15), items=240, over=False)
case("R1-9b", "iota seed 1 level 2 listed with an item count other than the plan's", True,
     any(x["lineage"] == "R1.iota_r4" and x["seed"] == "1" and any(l["level"] == 2 and l["items"] == 40 for l in x["levels"]) for x in EX["rows_with_an_item_count_other_than_the_plan"]))
drop("R1-9d", "R1.iota_r4", False)
rowcase("R1-10a", "a4:ccw_as_cw on compass_turns (EXCL stem-limited, prefix stripped): uncounted", one("R1b", "R1.compass_turns", 2, "a4:ccw_as_cw", "eff"), counted=False)
rowcase("R1-10b", "a3:abstain_as_yes (M, every lineage): uncounted", one("R1b", "R1.compass_turns", 2, "a3:abstain_as_yes", "eff"), counted=False)
rowcase("R1-10c", "ignore_180s in impl rows on compass_turns: uncounted", one("R1b", "R1.compass_turns", 2, "ignore_180s", "eff"), counted=False)
drop("R1-10d", "R1.compass_turns", False)
rowcase("R1-11", "ccw_as_cw on gamma (EXCL limited to compass_turns): counted", one("R1b", "R1.gamma_r6", 2, "ccw_as_cw", "eff"), counted=True, over=True)
drop("R1-11d", "R1.gamma_r6", True)
rowcase("R1-12", "'im:abstain_as_no' (prefix not a3:/a4:, so not bare-matched): counted", one("R1b", "R1.delta", 2, "im:abstain_as_no", "eff"), counted=True, over=True)
drop("R1-12d", "R1.delta", True)
U3 = F(11, 20000)
rowcase("R1-13", "R1c rule named abstain_as_no (R1c has no class): counted, 0.2 + 0.00055", one("R1c", "R1.kappa_r4", 0, "abstain_as_no", "eff"), excess=F(1, 5), margin=F(1, 5) + U3, counted=True, over=True)
drop("R1-13d", "R1.kappa_r4", True)
rowcase("R1-14", "R1c +0.149: 0.14955, kept", one("R1c", "R1.lambda_r4", 4, "lam", "eff"), margin=F(149, 1000) + U3, over=False)
drop("R1-14d", "R1.lambda_r4", False)
rowcase("R1-15", "R1c +0.150: 0.15055, dropped", one("R1c", "R1.mu_r4", 4, "mu_r", "eff"), margin=F(3, 20) + U3, over=True)
drop("R1-15d", "R1.mu_r4", True)
rowcase("R1-16", "anti 0.2000 drops", one("R1a", "R1.nu_r4", 6, "nu_anti", "anti"), excess=F(1, 5), over=True)
drop("R1-16d", "R1.nu_r4", True)
case("R1-17", "non-survivor R1.notasurvivor_r2 not read", 0, len([r for r in T if r["lineage"] == "R1.notasurvivor_r2"]))
case("R1-18", "mode_rate (R1b, 0.9 written on every row) read as no rule", 0, len([r for r in T if r["rule"] == "mode_rate"]))
# ---------------- M1
for cid, u, src, rule in [("M1-1a", "M1a", "own", "im:largest_share"), ("M1-1b", "M1a", "a3", "a3:largest_share"), ("M1-1c", "M1a", "a4", "im:largest_share"), ("M1-1d", "M1b", "results", "im:largest_share")]:
    rowcase(cid, f"{rule} ({u} {src}) on ratio_share: an entry, uncounted", one(u, "M1.ratio_share_r3", 2, rule, "vs_chance", source=src), counted=False)
case("M1-2", "key ending __within_applicable not read (M1a own and M1b)", 0, len([r for r in T if r["rule"].endswith("__within_applicable")]))
case("M1-2b", "fields mode_insample, answer_echoed_anywhere, one_op_best, asked_is_largest..., within_applicable not rules", 0,
     len([r for r in T if r["rule"] in ("mode_insample", "answer_echoed_anywhere", "one_op_best", "asked_is_largest_observed_vs_uniform", "within_applicable")]))
drop("M1-2d", "M1.ratio_share_r3", False)
rowcase("M1-3", "im:largest_share for gamma (pair is not an entry): counted", one("M1a", "M1.gamma_r3", 2, "im:largest_share", "vs_chance", source="own"), counted=True, over=True)
drop("M1-3d", "M1.gamma_r3", True)
rowcase("M1-4a", "vs chance: rate 0, kept", one("M1a", "M1.vsbase_r3", 3, "im:foo", "vs_chance", source="own"), excess=F(0), over=False)
rowcase("M1-4b", "base as the rule 'most frequent answer' vs chance: 2249/15000 + 1/20000, kept", one("M1a", "M1.vsbase_r3", 3, "base[own]", "vs_chance", source="own"), excess=F(2249, 15000), margin=F(2249, 15000) + U4, over=False)
rowcase("M1-4c", "vs base: -2249/15000 with two half units 1/10000 = 4501/30000 > 0.15, dropped", one("M1a", "M1.vsbase_r3", 3, "im:foo", "vs_base", source="own"), excess=F(-2249, 15000), margin=F(4501, 30000), over=True)
drop("M1-4d", "M1.vsbase_r3", True)
rowcase("M1-5", "M1b rate 0.16000 vs chance", one("M1b", "M1.vschance_r3", 1, "new:foo", "vs_chance"), excess=F(4, 25), margin=F(4, 25) + F(1, 200000), over=True)
drop("M1-5d", "M1.vschance_r3", True)
rowcase("M1-6", "M1c base 0.20000 read as a rule vs chance", one("M1c", "M1.base_r3", 6, "base", "vs_chance"), excess=F(1, 5), over=True)
drop("M1-6d", "M1.base_r3", True)
rowcase("M1-7", "M1 row N=30 (plan 100) in seed 1: (0.4*30 + 0.1*100*2)/230 = 16/115, kept", one("M1a", "M1.smalln_r3", 4, "im:sm", "vs_chance", source="own"), excess=F(16, 115), items=230, over=False)
case("M1-7b", "smalln listed with N other than the plan's", True, any(x["lineage"] == "M1.smalln_r3" and x["seed"] == "1" for x in EX["rows_with_an_item_count_other_than_the_plan"]))
drop("M1-7d", "M1.smalln_r3", False)
rowcase("M1-8a", "im:largest_le_sqrt on prime_factors: an entry", one("M1a", "M1.prime_factors_r3", 2, "im:largest_le_sqrt", "vs_chance", source="own"), counted=False)
rowcase("M1-8b", "a3:largest_le_sqrt (same name, definition differs, not an entry; amendment list empty): counted", one("M1a", "M1.prime_factors_r3", 2, "a3:largest_le_sqrt", "vs_chance", source="a3"), counted=True, over=True)
drop("M1-8d", "M1.prime_factors_r3", True)
case("M1-9", "non-survivor M1.zz_not_r3 not read", 0, len([r for r in T if r["lineage"] == "M1.zz_not_r3"]))
# ---------------- C1
U3c = F(1, 2000)
rowcase("C1-1", "EFF_F 0.200 under an alias id (C1.slices -> C1.slices_f4): counts, dropped", one("C1a", "C1.slices_f4", 2, "EFF_F", source="s5"), excess=F(1, 5), counted=True, over=True)
case("C1-1b", "slices_f4: every single rule and other measure below the bound", True,
     all(not r["over_bound"] for r in rows("C1a", "C1.slices_f4", 2, source="s5") if r["rule"] != "EFF_F"))
drop("C1-1d", "C1.slices_f4", True)
rowcase("C1-2a", "EFF_SM: uncounted (measure entry)", one("C1a", "C1.c_effsm", 2, "EFF_SM", source="s5"), counted=False)
rowcase("C1-2b", "s5 M.no_back: uncounted (literal entry)", one("C1a", "C1.c_effsm", 2, "M.no_back", source="s5"), counted=False)
rowcase("C1-2c", "s5 H.c_semantics: uncounted", one("C1a", "C1.c_effsm", 2, "H.c_semantics", source="s5"), counted=False)
drop("C1-2d", "C1.c_effsm", False)
rowcase("C1-3", "s5 M.not_entry (prefix M., not an entry): counted", one("C1a", "C1.c_mnot", 2, "M.not_entry", source="s5"), counted=True, over=True)
drop("C1-3d", "C1.c_mnot", True)
rowcase("C1-4", "s5 S.foo: round(0.25*16)+round(0.125*24) = 4+3 = 7 per seed -> 21/120", one("C1a", "C1.c_s5rec", 2, "S.foo", source="s5"), excess=F(7, 40), over=True)
drop("C1-4d", "C1.c_s5rec", True)
rowcase("C1-5", "s5 S.foo: 4 + round(0.042*24)=1 -> 15/120, kept", one("C1a", "C1.c_s5keep", 2, "S.foo", source="s5"), excess=F(1, 8), over=False)
drop("C1-5d", "C1.c_s5keep", False)
rowcase("C1-6", "s5 S.foo: 4 + round(0.083*24)=2 -> 18/120 = 0.15 recovered from 3-dp shares, + 0.0005: dropped (strict reading)", one("C1a", "C1.c_s5edge", 2, "S.foo", source="s5"), excess=F(3, 20), margin=F(3, 20) + U3c, over=True)
case("C1-7", "error-marker shape rows not read (s5, a3, battery)", 0, len([r for r in T if r["rule"] in ("S.bad",) or "RULE_ERROR" in r["rule"]]))
drop("C1-7d", "C1.c_err", False)
rowcase("C1-8", "a3 with alias_rc=1: fallback own file read (24/40 per seed)", one("C1a", "C1.c_a3fb", 3, "S.foo", source="a3"), excess=F(3, 5), over=True)
case("C1-8b", "fallback recorded for C1a c_a3fb, three seeds", 3, len([x for x in EX["a3_wrapper_fallbacks"] if x["unit"] == "C1a" and x["lineage"] == "C1.c_a3fb"]))
drop("C1-8d", "C1.c_a3fb", True)
rowcase("C1-9", "a3 with alias_rc=0: alias file read (2/40), own file ignored", one("C1a", "C1.c_a3ok", 3, "S.foo", source="a3"), excess=F(1, 20), over=False)
drop("C1-9d", "C1.c_a3ok", False)
rowcase("C1-10", "a3 hits 6,6,6 of 40: exactly 0.15 from counts, kept", one("C1a", "C1.c_a3exact", 3, "S.foo", source="a3"), excess=F(3, 20), margin=F(3, 20), over=False)
drop("C1-10d", "C1.c_a3exact", False)
rowcase("C1-11", "a3 hits 6,6,7: 19/120 just above, dropped", one("C1a", "C1.c_a3above", 3, "S.foo", source="a3"), excess=F(19, 120), over=True)
drop("C1-11d", "C1.c_a3above", True)
rowcase("C1-12", "battery S.no_back (BATTERY_MUT; entries are a3-only): counted", one("C1b", "C1.c_srcs", 4, "S.no_back", source="battery"), counted=True, over=True)
drop("C1-12d", "C1.c_srcs", True)
rowcase("C1-13a", "battery C.self_check: uncounted", one("C1b", "C1.c_srcs2", 4, "C.self_check", source="battery"), counted=False)
rowcase("C1-13b", "a3 S.no_back (A3_MUT): uncounted", one("C1a", "C1.c_srcs2", 3, "S.no_back", source="a3"), counted=False)
drop("C1-13d", "C1.c_srcs2", False)
rowcase("C1-14", "a3 C.self_check (entry is the battery's only): counted", one("C1a", "C1.c_srcs3", 3, "C.self_check", source="a3"), counted=True, over=True)
drop("C1-14d", "C1.c_srcs3", True)
rowcase("C1-15", "f5 M.no_back (not a closed-form entry): counted, 20/40", one("C1c", "C1.c_closed", 5, "M.no_back", source="f5"), excess=F(1, 2), counted=True, over=True)
drop("C1-15d", "C1.c_closed", True)
rowcase("C1-16a", "f5b M.no_even_branch: uncounted", one("C1c", "C1.c_closed2", 5, "M.no_even_branch", source="f5b"), counted=False)
rowcase("C1-16b", "f5b H.negative_step_as_positive: uncounted", one("C1c", "C1.c_closed2", 5, "H.negative_step_as_positive", source="f5b"), counted=False)
rowcase("C1-16c", "f5b F.keep 0.1000*40 = 4: 1/10 + 0.00005", one("C1c", "C1.c_closed2", 5, "F.keep", source="f5b"), excess=F(1, 10), margin=F(1, 10) + U4, over=False)
drop("C1-16d", "C1.c_closed2", False)
rowcase("C1-17", "battery MF_shape_cv {A 0.375 x 16 = 6, B 0}: 18/120 = 0.15 + 0.0005, dropped", one("C1b", "C1.c_msh", 4, "MF_shape_cv", source="battery"), excess=F(3, 20), margin=F(3, 20) + U3c, over=True)
drop("C1-17d", "C1.c_msh", True)
case("C1-18", "oracle_any_literal and best_generic_in_shape not read (0.9 / 1.0 written on every C1 row)", 0,
     len([r for r in T if r["rule"] in ("oracle_any_literal", "best_generic_in_shape", "BEST_generic_chosen", "MF_in_shape_cv")]))
drop("C1-18d", "C1.c_bkeep", False)
rowcase("C1-19", "a3 MF_printform_cv 0.200: counted", one("C1a", "C1.c_printform", 3, "MF_printform_cv", source="a3"), excess=F(1, 5), counted=True, over=True)
drop("C1-19d", "C1.c_printform", True)
case("C1-20", "non-survivor C1.zz_not not read", 0, len([r for r in T if r["lineage"] == "C1.zz_not"]))
# ---------------- whole
EXP_DROP = {"R1.beta_r5", "R1.gamma_r6", "R1.delta", "R1.eps_r4", "R1.zeta_r4", "R1.eta_r4", "R1.kappa_r4", "R1.mu_r4", "R1.nu_r4",
            "R2.b_open", "R2.d_yn", "R2.f_cond", "R2.h_sd", "R2.i_sdsum", "R2.k_klass2", "R2.l_construct", "R2.m_new",
            "M1.gamma_r3", "M1.vsbase_r3", "M1.vschance_r3", "M1.base_r3", "M1.prime_factors_r3",
            "C1.slices_f4", "C1.c_mnot", "C1.c_s5rec", "C1.c_s5edge", "C1.c_a3fb", "C1.c_a3above", "C1.c_srcs", "C1.c_srcs3", "C1.c_closed", "C1.c_msh", "C1.c_printform"}
case("ALL", "the set of lineages dropped equals the hand list", sorted(EXP_DROP), sorted(DROPPED))
case("ALL-2", "per-evaluation counts before/after", {"C1": [19, 10, 9], "M1": [7, 5, 2], "R1": [14, 9, 5], "R2": [14, 8, 6]},
     {ev: [v["before"], v["dropped"], v["after"]] for ev, v in EX["lineages_before_and_after_per_evaluation"].items()})
for r in res: print(f"{r[4]}  {r[0]:8s} {r[1]}\n          expected {r[2]}\n          got      {r[3]}")
print(f"\nCASES {len(res)}  PASS {sum(r[4] == 'PASS' for r in res)}  FAIL {sum(r[4] == 'FAIL' for r in res)}")
