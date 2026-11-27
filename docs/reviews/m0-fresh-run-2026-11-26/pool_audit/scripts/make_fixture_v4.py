"""Auditor's made-up outputs for the eleven units, in the output forms of the committed scripts (b78e58b1), with a small made-up plan and
survivor list in run_plan.json's schema. Every figure is chosen by hand; expected results are written literally in check_cases.py.
usage: python3 -I make_fixture.py OUTDIR [VARIANT]   VARIANT in main, stop_r2a_missing, stop_m1b_level, stop_r1c_six, stop_a3_log, stop_f5_missing"""
import hashlib, json, os, sys

OUT, VARIANT = os.path.abspath(sys.argv[1]), (sys.argv[2] if len(sys.argv) > 2 else "main")
os.makedirs(OUT, exist_ok=False)
SEEDS = ["1", "2", "3"]
LV = range(7)
P = {"R1": 100, "R2": 40, "M1": 100, "C1": 40}  # plan items per level (made up)
SURV = {
    "R1": ["R1.compass_turns", "R1.alpha_r4", "R1.beta_r5", "R1.gamma_r6", "R1.delta", "R1.eps_r4", "R1.zeta_r4", "R1.eta_r4", "R1.theta_r4",
           "R1.iota_r4", "R1.kappa_r4", "R1.lambda_r4", "R1.mu_r4", "R1.nu_r4"],
    "R2": ["R2.a_open", "R2.b_open", "R2.c_yn", "R2.d_yn", "R2.e_oneseed", "R2.f_cond", "R2.g_sd", "R2.h_sd", "R2.i_sdsum", "R2.j_klass",
           "R2.k_klass2", "R2.l_construct", "R2.count_divisible", "R2.m_new"] + (["R2.crt_smallest"] if VARIANT == "classes2" else []),
    "M1": ["M1.ratio_share_r3", "M1.gamma_r3", "M1.vsbase_r3", "M1.vschance_r3", "M1.base_r3", "M1.smalln_r3", "M1.prime_factors_r3"],
    "C1": ["C1.slices_f4", "C1.c_effsm", "C1.c_mnot", "C1.c_s5rec", "C1.c_s5keep", "C1.c_s5edge", "C1.c_err", "C1.c_a3fb", "C1.c_a3ok", "C1.c_a3exact",
           "C1.c_a3above", "C1.c_srcs", "C1.c_srcs2", "C1.c_srcs3", "C1.c_closed", "C1.c_closed2", "C1.c_msh", "C1.c_bkeep", "C1.c_printform"],
}
def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "x") as f:
        f.write(text)
def wj(path, obj): w(path, json.dumps(obj, indent=1))
def d(u, s): return os.path.join(OUT, "outputs", u, "seed" + s)

surv_path = os.path.join(OUT, "survivors.json")
wj(surv_path, {"evaluations": SURV})
surv_sha = hashlib.sha256(open(surv_path, "rb").read()).hexdigest()
wj(os.path.join(OUT, "amend.json"), {"commit": "made-up", "entries": [{"unit": "R1a", "lineage": "R1.alpha_r4", "rule": "my_rule"}]})

# ---------------------------------------------------------------- R1a, R1b: r1_rows
FEAT = ["R1.compass_turns", "R1.alpha_r4"]
def r1row(lid, lv, h, eff, anti=0.0, n=100, fired=50, acc=0.5, mode_rate=None):
    r = {"lineage": lid, "level": lv, "heuristic": h, "n": n, "chance": 0.5, "fired": fired, "acc_fired": acc, "eff": eff, "anti": anti}
    if mode_rate is not None: r["mode_rate"] = mode_rate
    return r
for u in ["R1a", "R1b"]:
    for s in SEEDS:
        for lid in SURV["R1"] + ["R1.notasurvivor_r2"]:
            aud, impl, feat = [], [], []
            for lv in LV:
                n = 40 if (lid == "R1.iota_r4" and s == "1" and lv == 2 and u == "R1a") else 100
                mr = 0.9 if u == "R1b" else None
                aud.append(r1row(lid, lv, "base_rule", 0.0, n=n, mode_rate=mr))
                impl.append(r1row(lid, lv, "base_rule", 0.0, n=n))
                if lid in FEAT: feat.append({"lineage": lid, "level": lv, "heuristic": "feat:x", "eff": 0.0, "anti": None, "acc_fired": None, "fired": 100, "n": 100})
                # ---- cases (unit R1a unless stated)
                if u == "R1a":
                    if lid == "R1.notasurvivor_r2": aud.append(r1row(lid, lv, "big", 0.9))
                    if lid in ("R1.alpha_r4", "R1.beta_r5") and lv == 3: aud.append(r1row(lid, lv, "my_rule", 0.3))
                    if lid == "R1.alpha_r4": aud.append(r1row(lid, lv, "abstain_as_no", 0.5, fired=100, acc=1.0))
                    if lid == "R1.eps_r4": aud.append(r1row(lid, lv, "exact_x", 0.5, fired=100, acc=1.0))
                    if lid == "R1.zeta_r4" and lv == 1: impl.append(r1row(lid, lv, "z_rule", 0.15))
                    if lid == "R1.compass_turns" and lv == 1: impl.append(r1row(lid, lv, "c_ok", 0.1499))
                    if lid == "R1.eta_r4" and lv == 5: aud.append(r1row(lid, lv, "e_neg", -0.1501, anti=0.1499))
                    if lid == "R1.theta_r4" and lv == 4 and s == "1": aud.append(r1row(lid, lv, "one_seed", 0.3))
                    if VARIANT == "classes2" and lid == "R1.theta_r4" and lv == 0: aud.append(r1row(lid, lv, "a3:latest_start_first", 0.4))
                    if lid == "R1.iota_r4" and lv == 2: aud.append(r1row(lid, lv, "small_n", 0.3 if s == "1" else 0.1, n=n))
                    if lid == "R1.nu_r4" and lv == 6: aud.append(r1row(lid, lv, "nu_anti", 0.0, anti=0.2))
                if u == "R1b":
                    if lid == "R1.compass_turns" and lv == 2:
                        aud.append(r1row(lid, lv, "a4:ccw_as_cw", 0.4, mode_rate=0.9)); aud.append(r1row(lid, lv, "a3:abstain_as_yes", 0.4, mode_rate=0.9))
                        impl.append(r1row(lid, lv, "ignore_180s", 0.4))
                    if lid == "R1.gamma_r6" and lv == 2: aud.append(r1row(lid, lv, "ccw_as_cw", 0.4, mode_rate=0.9))
                    if lid == "R1.delta" and lv == 2: impl.append(r1row(lid, lv, "im:abstain_as_no", 0.4))
            w(os.path.join(d(u, s), f"{lid}.aud.jsonl"), "".join(json.dumps(r) + "\n" for r in aud))
            w(os.path.join(d(u, s), f"{lid}.impl.jsonl"), "".join(json.dumps(r) + "\n" for r in impl))
            w(os.path.join(d(u, s), f"{lid}.feat.jsonl"), "".join(json.dumps(r) + "\n" for r in feat))
# ---------------------------------------------------------------- R1c: stdout lines, exactly as new_rules_final.py prints them
R1C = ["R1.kappa_r4", "R1.lambda_r4", "R1.mu_r4"]
for s in SEEDS:
    lines = []
    def line(lid, h, effs, antis): lines.append(f"{lid:36s} {h[:60]:60s} eff " + " ".join(f"{e:+.3f}" for e in effs) + "   anti " + " ".join(f"{a:+.3f}" for a in antis))
    for lid in R1C:
        line(lid, "base_new", [0.0] * 7, [0.0] * 7)
    line("R1.kappa_r4", "abstain_as_no", [0.2] + [0.0] * 6, [0.0] * 7)
    line("R1.lambda_r4", "lam", [0.0] * 4 + [0.149] + [0.0] * 2, [0.0] * 7)
    line("R1.mu_r4", "mu_r", [0.0] * 4 + [0.150] + [0.0] * 2, [0.0] * 7)
    line("R1.notasurvivor_r2", "big", [0.9] * 7, [0.0] * 7)
    if VARIANT == "stop_r1c_six" and s == "2":
        line("R1.lambda_r4", "only_six_levels", [0.0] * 6, [0.0] * 6)
    w(os.path.join(d("R1c", s), "stdout.txt"), "\n".join(lines) + "\n")
# ---------------------------------------------------------------- R2a, R2b: r2_json
def rr(k, napp, n, r2a, nerr=0):
    v = {"k": k, "napp": napp, "nerr": nerr}
    if r2a: v["acc_all"] = k / n; v["acc_app"] = k / napp if napp else 0.0
    return v
YN = {"R2.c_yn", "R2.d_yn"}
SD = {"R2.g_sd", "R2.h_sd"}
SDR = "[a3] removal by deleting the minimum and keeping the order of the rest"
R2A_L = ["R2.a_open", "R2.b_open", "R2.c_yn", "R2.d_yn", "R2.e_oneseed", "R2.j_klass", "R2.k_klass2", "R2.l_construct"]
NEWPART = "[NEW] (partial) largest modulus: try r, r+m, r+2m against the other congruences, else r"
NEWP = "[NEW] (P) misread: each distinct value counted once (the wording now excludes it)"
for u, fname, r2a in [("R2a", "r2a.json", True), ("R2b", "f_rules.json", False)]:
    for s in SEEDS:
        lins = {}
        for lid in SURV["R2"] + ["R2.zz_not"]:
            lvs = {}
            if VARIANT == "stop_r2a_missing" and u == "R2a" and s == "2" and lid == "R2.a_open":
                continue
            for lv in LV:
                at = "yn" if lid in YN else "number"
                shapes = {"removals=0": 20, "removals=1": 20} if lid in SD else {"-": 40}
                ent = {}
                for sh, n in shapes.items():
                    e = {"n": n, "answer_type": at, "distinct_answers": 5, "rules": {}}
                    if r2a and at == "yn": e["yes_share"] = 0.5
                    e["rules"]["most frequent answer (train draw)"] = rr(n // 2 if at == "yn" else 1, n, n, r2a)
                    e["rules"]["[impl] base"] = rr(n // 2 if at == "yn" else 0, n, n, r2a)
                    mine = (u == "R2a") == (lid in R2A_L)
                    if mine and lv == 2:
                        if lid == "R2.a_open": e["rules"]["[impl] x"] = rr(6, 40, n, r2a)
                        if lid == "R2.b_open": e["rules"]["[impl] x"] = rr(7 if s == "3" else 6, 40, n, r2a)
                        if lid == "R2.c_yn": e["rules"]["[mine] yn hi"] = rr(26, 40, n, r2a); e["rules"]["[mine] yn lo"] = rr(14, 40, n, r2a)
                        if lid == "R2.d_yn": e["rules"]["[mine] yn lo2"] = rr(13 if s == "3" else 14, 40, n, r2a)
                        if lid == "R2.e_oneseed" and s == "2": e["rules"]["[impl] once"] = rr(18, 40, n, r2a)
                        if lid == "R2.f_cond": e["rules"]["[mine] [cond] foo"] = rr(5, 20, n, r2a)
                        if lid == "R2.g_sd": e["rules"][SDR] = rr(20 if sh == "removals=0" else 2, 20, n, r2a)
                        if lid == "R2.h_sd": e["rules"][SDR] = rr(0 if sh == "removals=0" else 4, 20, n, r2a)
                        if lid == "R2.i_sdsum": e["rules"][SDR] = rr(8, 40, n, r2a)
                        if lid == "R2.zz_not": e["rules"]["[impl] big"] = rr(40, 40, n, r2a)
                    if mine and lid == "R2.j_klass" and lv in (0, 1):
                        e["rules"]["[a3] rules in reverse order"] = rr(40, 40, n, r2a)
                        e["rules"]["[mine] alpha (P) beta"] = rr(40, 40, n, r2a)
                        e["rules"]["[impl] uses letter pairs here"] = rr(40, 40, n, r2a)
                        if lv == 0: e["rules"]["[a3] only the first rule"] = rr(40, 40, n, r2a)
                    if VARIANT == "classes2" and mine and lid == "R2.a_open" and lv == 5: e["rules"]["[a3] ignore reverses"] = rr(40, 40, n, r2a)
                    if mine and lid == "R2.k_klass2" and lv == 1: e["rules"]["[a3] only the first rule"] = rr(40, 40, n, r2a)
                    if mine and lid == "R2.l_construct" and lv == 1: e["rules"]["[mine] t mod 10 applications"] = rr(40, 40, n, r2a)
                    ent[sh] = e
                lvs[str(lv)] = ent
            lins[lid] = lvs
        wj(os.path.join(d(u, s), fname), {"n": 40, "seeds": "made-up", "lineages": lins})
for s in SEEDS:  # f_rules_new.json (R2b second command): NEW rules only, for its two lineages
    lins = {}
    for lid in ["R2.count_divisible", "R2.m_new"] + (["R2.crt_smallest"] if VARIANT == "classes2" else []):
        lins[lid] = {str(lv): {"-": {"n": 40, "answer_type": "number", "rules": {"[NEW] (cue) base": {"k": 0, "napp": 40, "nerr": 0},
                     **({NEWP: {"k": 40, "napp": 40, "nerr": 0}} if lv == 3 else {}), **({NEWPART: {"k": 40, "napp": 40, "nerr": 0}} if lv == 4 and VARIANT == "classes2" else {})}}} for lv in LV}
    wj(os.path.join(d("R2b", s), "f_rules_new.json"), {"n": 40, "lineages": lins})
# ---------------------------------------------------------------- M1a: m1_battery; M1b, M1c: m1_results
def m1own(N=100, base=0.05, rates=None):
    r = {"base_r": 0.0, **(rates or {})}
    return {"N": N, "base": base, "mode_insample": 0.99, "halfwidth95": {k: 0.01 for k in r}, "rates": r, "minus_base": {k: round(v - base, 4) for k, v in r.items()}, "answer_echoed_anywhere": 0.99}
def m1a4(base=0.05, rates=None):
    r = {"base_r": 0.0, **(rates or {})}
    return {"N": 100, "base": base, "best_echo": ["first|first+0"], "answer_echoed_anywhere": 0.99, "rates": r, "minus_base": {k: round(v - base, 4) for k, v in r.items()}, "within_applicable": {"base_r": [0.99, 10]}}
def m1a3(base=0.05, rates=None):
    r = {"base_r": 0.0, **(rates or {})}
    return {"N": 100, "base": base, "rates": r, "minus_base": {k: round(v - base, 4) for k, v in r.items()}}
for s in SEEDS:
    raw = {"own": {}, "a4": {}, "a3": {}}
    for lid in SURV["M1"] + ["M1.zz_not_r3"]:
        raw["own"][lid], raw["a4"][lid], raw["a3"][lid] = {}, {}, {}
        for lv in LV:
            own_r, a4_r, a3_r, own_base, N = {}, {}, {}, 0.05, 100
            if lv == 2:
                if lid == "M1.ratio_share_r3":
                    own_r = {"largest_share": 0.9, "x__within_applicable": 0.9}; a3_r = {"largest_share": 0.9}; a4_r = {"im:largest_share": 0.9}
                if lid == "M1.gamma_r3": own_r = {"largest_share": 0.9}
                if lid == "M1.prime_factors_r3": own_r = {"largest_le_sqrt": 0.9}; a3_r = {"largest_le_sqrt": 0.9}
                if lid == "M1.zz_not_r3": own_r = {"big": 0.9}
            if lv == 3 and lid == "M1.vsbase_r3":
                own_base = 0.15 if s == "2" else 0.1499; own_r = {"foo": 0.0}
            if VARIANT == "echo" and lv == 5 and lid == "M1.ratio_share_r3":
                own_r = {("echo_best_position[max/last]" if s == "3" else "echo_best_position[max/max]"): 0.2}
            if lv == 4 and lid == "M1.smalln_r3":
                N = 30 if s == "1" else 100; own_r = {"sm": 0.4 if s == "1" else 0.1}
            raw["own"][lid][str(lv)] = m1own(N, own_base, own_r)
            raw["a4"][lid][str(lv)] = m1a4(rates=a4_r)
            raw["a3"][lid][str(lv)] = m1a3(rates=a3_r)
        raw["a3"][lid]["a3_skipped_items"] = 0
    wj(os.path.join(d("M1a", s), "battery.json"), {"n": 100, "seeds": {"own": 410302, "a4": 17, "a3": 5}, "exclusions": {}, "raw": raw, "summary": {}})
    for u in ["M1b", "M1c"]:
        res = {}
        for lid in SURV["M1"] + ["M1.zz_not_r3"]:
            res[lid] = {}
            for lv in LV:
                if VARIANT == "stop_m1b_level" and u == "M1b" and s == "3" and lid == "M1.gamma_r3" and lv == 5:
                    continue
                rates, base = {"base_r": 0.0, "base_r__within_applicable": 0.9}, 0.05
                if lv == 2 and lid == "M1.ratio_share_r3" and u == "M1b": rates["im:largest_share"] = 0.9
                if lv == 1 and lid == "M1.vschance_r3" and u == "M1b": rates["new:foo"] = 0.16
                if lv == 6 and lid == "M1.base_r3" and u == "M1c": base = 0.2
                res[lid][str(lv)] = {"N": 100, "base": base, "rates": rates, "minus_base": {k: round(v - base, 5) for k, v in rates.items()},
                                     "within_applicable": {}, "a3_skipped_items": 0, "one_op_best": ["a", "b"]}
            if lid == "M1.ratio_share_r3":
                for lv in LV: res[lid][str(lv)]["asked_is_largest_observed_vs_uniform"] = 0.9
        wj(os.path.join(d(u, s), "out.json"), {"mode": "fresh", "N": 100, "seed": 1, "label": "made-up", "results": res})
# ---------------------------------------------------------------- C1: s5 (C1a, C1c), a3 (C1a, C1c), battery (C1b), closed forms (C1c)
SH = {"A": 16, "B": 24}
def s5row(lid, lv, unit):
    r = {"n": 40, "parse_fail": 0, "shapes": dict(SH), "distinct_keys": 5, "MF": 0.0, "MFsh": 0.0, "EFF_S": 0.0, "EFF_SM": 0.0, "EFF_F": 0.0,
         "rules": {"A|S.base": {"rate_in_shape": 0.0, "share_of_level": 0.0, "n_shape": 16}, "B|S.base": {"rate_in_shape": 0.0, "share_of_level": 0.0, "n_shape": 24},
                   "A|MF_in_shape_cv": {"rate_in_shape": 0.9, "n_shape": 16}}}
    if unit == "C1a" and lv == 2:
        R = r["rules"]
        if lid == "C1.slices_f4":
            r["EFF_F"] = 0.2
            R["A|S.lo"] = {"rate_in_shape": 0.25, "share_of_level": 0.1, "n_shape": 16}; R["B|F.lo"] = {"rate_in_shape": 0.125, "share_of_level": 0.075, "n_shape": 24}
            r["EFF_S"] = 0.1; r["MF"] = 0.1; r["MFsh"] = 0.1
        if lid == "C1.c_effsm":
            r["EFF_SM"] = 0.5; R["A|M.no_back"] = {"rate_in_shape": 1.0, "share_of_level": 0.4, "n_shape": 16}; R["B|H.c_semantics"] = {"rate_in_shape": 1.0, "share_of_level": 0.6, "n_shape": 24}
        if lid == "C1.c_mnot": R["A|M.not_entry"] = {"rate_in_shape": 1.0, "share_of_level": 0.4, "n_shape": 16}
        if lid == "C1.c_s5rec":
            R["A|S.foo"] = {"rate_in_shape": 0.25, "share_of_level": 0.1, "n_shape": 16}; R["B|S.foo"] = {"rate_in_shape": 0.125, "share_of_level": 0.075, "n_shape": 24}
        if lid == "C1.c_s5keep":
            R["A|S.foo"] = {"rate_in_shape": 0.25, "share_of_level": 0.1, "n_shape": 16}; R["B|S.foo"] = {"rate_in_shape": 0.042, "share_of_level": 0.025, "n_shape": 24}
        if lid == "C1.c_s5edge":
            R["A|S.foo"] = {"rate_in_shape": 0.25, "share_of_level": 0.1, "n_shape": 16}; R["B|S.foo"] = {"rate_in_shape": 0.083, "share_of_level": 0.05, "n_shape": 24}
        if lid == "C1.c_err": R["RULE_ERROR:ValueError:x|S.bad"] = {"rate_in_shape": 1.0, "share_of_level": 1.0, "n_shape": 40}
    return r
S5_ALIAS = {"C1.slices_f4": "C1.slices"}
for u in ["C1a", "C1c"]:
    for s in SEEDS:
        wj(os.path.join(d(u, s), "s5.json"), {S5_ALIAS.get(lid, lid): {str(lv): s5row(lid, lv, u) for lv in LV} for lid in SURV["C1"] + ["C1.zz_not"]})
def a3lev(lid, lv, unit, which):
    S = {"A|S.base": {"hit": 0, "applies": 16, "n_shape": 16, "rate_in_shape": 0.0, "ci": [0.0, 0.2], "share_of_level": 0.4, "mf_in_shape_cv": 0.9}}
    r = {"n": 40, "MF_cv": 0.0, "MF_printform_cv": 0.0, "MF_shape_cv": 0.0, "BEST_generic_cv": 0.0, "BEST_generic_chosen": ["g1", "g2"], "oracle_any_literal": 0.9,
         "shapes": dict(SH), "S": S, "distinct_keys": 5}
    def add(rule, hit): S["B|" + rule] = {"hit": hit, "applies": 24, "n_shape": 24, "rate_in_shape": round(hit / 24, 3), "ci": [0.0, 1.0], "share_of_level": 0.6, "mf_in_shape_cv": 0.0}
    if unit == "C1a" and lv == 3:
        if lid == "C1.c_a3fb": add("S.foo", 0 if which == "alias" else 24)
        if lid == "C1.c_a3ok": add("S.foo", 2 if which == "alias" else 40)
        if lid == "C1.c_a3exact": add("S.foo", 6)
        if lid == "C1.c_srcs2": add("S.no_back", 24)
        if lid == "C1.c_srcs3": add("C.self_check", 24)
        if lid == "C1.c_printform": r["MF_printform_cv"] = 0.2
        if lid == "C1.c_bkeep": r["oracle_any_literal"] = 1.0
        if lid == "C1.c_err": S["RULE_ERROR:ValueError:x|S.bad"] = {"hit": 40, "applies": 40, "n_shape": 40, "rate_in_shape": 1.0, "ci": [0.9, 1.0], "share_of_level": 1.0, "mf_in_shape_cv": 0.0}
    return r
def a3above_hits(s): return 7 if s == "3" else 6
PER_SURV = {}
for lid in SURV["C1"]:
    tag = lid.split(".", 1)[1]
    PER_SURV[lid] = {"run_log_key": lid, "primary_file": f"a3/{tag}__alias.json", "primary_key": "C1.alias_" + tag, "fallback_file": f"a3/{tag}__own.json", "fallback_key": lid}
for u in ["C1a", "C1c"]:
    for s in SEEDS:
        log = {}
        for lid in SURV["C1"]:
            ps = PER_SURV[lid]
            if VARIANT == "stop_a3_log" and u == "C1c" and s == "1" and lid == "C1.c_srcs":
                pass
            else:
                fb = u == "C1a" and lid == "C1.c_a3fb"
                log[lid] = {"alias": ps["primary_key"], "alias_rc": 1 if fb else 0, "alias_err": "Traceback: AttributeError (made up)" if fb else "", "own_rc": 0 if fb else None, "own_err": ""}
            body_alias = {str(lv): a3lev(lid, lv, u, "alias") for lv in LV}
            body_own = {str(lv): a3lev(lid, lv, u, "own") for lv in LV}
            if lid == "C1.c_a3above" and u == "C1a":
                for which, b in (("alias", body_alias), ("own", body_own)):
                    b["3"]["S"]["B|S.foo"] = {"hit": a3above_hits(s), "applies": 24, "n_shape": 24, "rate_in_shape": 0.25, "ci": [0, 1], "share_of_level": 0.6, "mf_in_shape_cv": 0.0}
            wj(os.path.join(d(u, s), ps["primary_file"]), {ps["primary_key"]: body_alias})
            wj(os.path.join(d(u, s), ps["fallback_file"]), {ps["fallback_key"]: body_own})
        wj(os.path.join(d(u, s), "a3", "run_log.json"), log)
for s in SEEDS:
    bat = {}
    for lid in SURV["C1"] + ["C1.zz_not"]:
        bat[lid] = {}
        for lv in LV:
            S = {"A|S.base": {"hit": 0, "n_shape": 16, "rate": 0.0}}
            r = {"n": 40, "MF_cv": 0.0, "MF_shape_cv": {"A": 0.0, "B": 0.0}, "BEST_generic_cv": 0.0, "BEST_generic_chosen": ["g", "g"],
                 "best_generic_in_shape": {"A": {"rule": "g", "rate": 1.0}, "B": {"rule": "g", "rate": 1.0}}, "oracle_any_literal": 0.9, "shapes": dict(SH), "S": S,
                 "distinct_keys": 5, "retries": 0}
            if lv == 4:
                if lid == "C1.c_srcs": S["B|S.no_back"] = {"hit": 24, "n_shape": 24, "rate": 1.0}
                if lid == "C1.c_srcs2": S["B|C.self_check"] = {"hit": 24, "n_shape": 24, "rate": 1.0}
                if lid == "C1.c_msh": r["MF_shape_cv"] = {"A": 0.375, "B": 0.0}
                if lid == "C1.c_err": S["RULE_ERROR:KeyError:y|S.bad"] = {"hit": 40, "n_shape": 40, "rate": 1.0}
                if lid == "C1.zz_not": S["B|S.big"] = {"hit": 40, "n_shape": 24, "rate": 1.0}
            bat[lid][str(lv)] = r
    wj(os.path.join(d("C1b", s), "battery.json"), bat)
CLOSED = ["C1.c_closed", "C1.c_closed2"]
for s in SEEDS:
    for fname in ["f5.json", "f5b.json"]:
        out = {}
        for lid in CLOSED:
            if VARIANT == "stop_f5_missing" and fname == "f5.json" and s == "2" and lid == "C1.c_closed":
                continue
            pl = {str(lv): {"F.base": 0.0} for lv in LV}
            if fname == "f5.json" and lid == "C1.c_closed": pl["5"]["M.no_back"] = 0.5
            if fname == "f5b.json" and lid == "C1.c_closed2": pl["5"].update({"M.no_even_branch": 0.9, "H.negative_step_as_positive": 0.9, "F.keep": 0.1})
            out[lid] = {"per_level": pl, "n_per_level": {str(lv): 40 for lv in LV}, "errors": 0}
        out["C1.zz_not"] = {"per_level": {str(lv): {"F.big": 1.0} for lv in LV}, "n_per_level": {str(lv): 40 for lv in LV}, "errors": 0}
        wj(os.path.join(d("C1c", s), fname), out)
# ---------------------------------------------------------------- the plan (schema of run_plan.json; only the fields the pooling script reads, plus evaluation)
def idm(ev, extra=None): return {**{x: x for x in SURV[ev]}, **(extra or {})}
R1KINDS = {"aud": {"glob": "*.aud.jsonl", "must_contain": SURV["R1"]}, "impl": {"glob": "*.impl.jsonl", "must_contain": SURV["R1"]},
           "feat": {"glob": "*.feat.jsonl", "must_contain": FEAT}}
R2_ALL = SURV["R2"]
outputs = {
    "R1a": [{"form": "r1_rows", "id_map": idm("R1"), "kinds": R1KINDS}],
    "R1b": [{"form": "r1_rows", "id_map": idm("R1"), "kinds": R1KINDS}],
    "R1c": [{"form": "r1c_stdout", "file": "stdout.txt", "id_map": {x: x for x in R1C}, "must_contain": R1C}],
    "R2a": [{"form": "r2_json", "file": "r2a.json", "variant": "r2a", "id_map": idm("R2"), "must_contain": R2_ALL}],
    "R2b": [{"form": "r2_json", "file": "f_rules.json", "variant": "f_rules", "id_map": idm("R2"), "must_contain": R2_ALL},
            {"form": "r2_json", "file": "f_rules_new.json", "variant": "f_rules_new", "id_map": {x: x for x in ["R2.count_divisible", "R2.m_new"] + (["R2.crt_smallest"] if VARIANT == "classes2" else [])},
             "must_contain": ["R2.count_divisible", "R2.m_new"] + (["R2.crt_smallest"] if VARIANT == "classes2" else [])}],
    "M1a": [{"form": "m1_battery", "file": "battery.json", "id_map": idm("M1"), "must_contain": SURV["M1"]}],
    "M1b": [{"form": "m1_results", "file": "out.json", "id_map": idm("M1"), "must_contain": SURV["M1"]}],
    "M1c": [{"form": "m1_results", "file": "out.json", "id_map": idm("M1"), "must_contain": SURV["M1"]}],
    "C1a": [{"form": "c1_a3", "run_log": "a3/run_log.json", "per_survivor": PER_SURV, "must_contain": SURV["C1"]},
            {"form": "c1_s5", "file": "s5.json", "id_map": {**idm("C1"), "C1.slices": "C1.slices_f4"}, "must_contain": SURV["C1"]}],
    "C1b": [{"form": "c1_battery", "file": "battery.json", "id_map": idm("C1"), "must_contain": SURV["C1"]}],
    "C1c": [{"form": "c1_a3", "run_log": "a3/run_log.json", "per_survivor": PER_SURV, "must_contain": SURV["C1"]},
            {"form": "c1_closed", "file": "f5.json", "id_map": {x: x for x in CLOSED}, "must_contain": CLOSED},
            {"form": "c1_closed", "file": "f5b.json", "id_map": {x: x for x in CLOSED}, "must_contain": CLOSED},
            {"form": "c1_s5", "file": "s5.json", "id_map": {**idm("C1"), "C1.slices": "C1.slices_f4"}, "must_contain": SURV["C1"]}],
}
order = ["R1a", "R1b", "R1c", "R2a", "R2b", "M1a", "M1b", "M1c", "C1a", "C1b", "C1c"]
plan = {"unit_order": order, "dry_run_exclusions": [], "survivor_list": {"path": surv_path, "sha256": surv_sha},
        "units": {u: {"evaluation": u[:2], "items_per_level": {"dry": 20, "run": P[u[:2]]}, "outputs": outputs[u],
                      "runs": {s: {"output_dir": d(u, s)} for s in SEEDS}} for u in order}}
wj(os.path.join(OUT, "plan.json"), plan)
print("fixture written:", OUT, VARIANT)
