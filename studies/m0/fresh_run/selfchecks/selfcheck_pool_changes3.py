"""Self-checks of the changes R-56 (M1a bracket reading), R-57 (rates within one shape), R-58 (hash checks, dry exclusions). Made-up outputs only."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import selfcheck_pool as sc  # noqa: E402
from selfcheck_pool import SEEDS, L7, Env, check, find, jdump, jo, table  # noqa: E402


def m1a_env(name, own_rates_by_seed, lid="M1.ages_r3", a4=None, a3=None):
    e = Env(name)
    e.surv = {"M1": [lid]}
    e.unit("M1a", "M1", 4000, [{"form": "m1_battery", "file": "battery.json", "id_map": {lid: lid}, "must_contain": [lid]}])
    for s in SEEDS:
        sec = lambda rates: {str(v): {"N": 4000, "base": 0.02, "rates": rates, "minus_base": {k: 0.0 for k in rates}, "mode_insample": 0.1, "answer_echoed_anywhere": 0.1, "halfwidth95": {k: 0.0 for k in rates}} for v in L7}
        a4s = lambda rates: {str(v): {"N": 4000, "base": 0.02, "best_echo": ["a", "b"], "answer_echoed_anywhere": 0.1, "rates": rates, "minus_base": {k: 0.0 for k in rates}, "within_applicable": {}} for v in L7}
        a3s = lambda rates: {**{str(v): {"N": 4000, "base": 0.02, "rates": rates, "minus_base": {k: 0.0 for k in rates}} for v in L7}, "a3_skipped_items": 0}
        jdump(e.d("M1a", s) + "/battery.json", {"n": 4000, "seeds": {}, "exclusions": {}, "summary": {}, "raw": {"own": {lid: sec(own_rates_by_seed[s])}, "a4": {lid: a4s((a4 or {}).get(s, {"q": 0.01}))}, "a3": {lid: a3s((a3 or {}).get(s, {"q": 0.01}))}}})
    return e


def t_bracket():
    # the audit's case: 0.20 in every seed, named [first/second] in seeds 1 and 2 and [first/first] in seed 3
    names = {"1": "echo_best_position[first/second]", "2": "echo_best_position[first/second]", "3": "echo_best_position[first/first]"}
    e = m1a_env("br1", {s: {names[s]: 0.2, "q": 0.01} for s in SEEDS})
    code, err, so, out = e.run()
    T = table(out)
    lid = "M1.ages_r3"
    w = find(T, unit="M1a", source="own", rule="im:echo_best_position[first/second]", level=1, reading="vs_chance")[0]
    st = find(T, unit="M1a", source="own", rule="im:echo_best_position", level=1, reading="vs_chance")[0]
    check("R-56: as written, the bracketed name pools to 2/15 (0.20 in two of three seeds) and does not drop", sc.F(w["pooled_figure"]) == sc.Fraction(2, 15) and not w["over_bound"], w)
    check("R-56: under the name without the bracket the three seeds are one rule: 0.20 over 12000 items, with the section prefix im:, and drops", sc.F(st["pooled_figure"]) == sc.Fraction(1, 5) and st["items"] == 12000 and st["over_bound"] and st["bracket_stripped"] and sc.F(st["rounding_uncertainty"]) == sc.Fraction(1, 20000), st)
    vb = find(T, unit="M1a", source="own", rule="im:echo_best_position", level=1, reading="vs_base")
    check("R-56: the stripped rule is also read against base", len(vb) == 1 and vb[0]["bracket_stripped"])
    ex = jo(out, "report_extras.json")
    ch = ex["m1a_bracket_second_reading_lineages_whose_outcome_differs"]
    check("R-56: the lineage whose outcome differs (kept as written, dropped under the second reading) is listed", len(ch) == 1 and ch[0]["lineage"] == lid and ch[0]["dropped_without_it"] is False, ch)
    check("R-56: the lineage is dropped (the larger excess decides)", [d["lineage"] for d in jo(out, "dropped.json")] == [lid])
    check("R-56: the stripped rows are listed", any(r["stripped_name"] == "im:echo_best_position" for r in ex["m1a_bracket_second_reading_rows"]))
    # an a3-section key takes a3:; the entry lookup uses the stripped prefixed name (ratio_share a3:largest_share is an entry)
    lr = "M1.ratio_share_r3"
    e = m1a_env("br2", {s: {"q": 0.01} for s in SEEDS}, lid=lr, a3={s: {"largest_share[x]": 0.5} for s in SEEDS})
    code, err, so, out = e.run()
    T = table(out)
    a = find(T, unit="M1a", lineage=lr, source="a3", rule="a3:largest_share", level=2, reading="vs_chance")[0]
    b = find(T, unit="M1a", lineage=lr, source="a3", rule="a3:largest_share[x]", level=2, reading="vs_chance")[0]
    check("R-56: the stripped name takes the section prefix and is looked up in the class table: an entry matches it (uncounted); the as-written name is not an entry (counts)", not a["counted"] and "largest_share" in a["class_entry"] and b["counted"], (a, b))
    # a name that matches no entry counts
    e = m1a_env("br3", {s: {"q": 0.01} for s in SEEDS}, a3={s: {"zzz[1]": 0.01} for s in SEEDS})
    code, err, so, out = e.run()
    T = table(out)
    check("R-56: a stripped name that matches no entry counts", find(T, unit="M1a", rule="a3:zzz", level=1, reading="vs_chance")[0]["counted"] and jo(out, "dropped.json") == [])
    check("R-56: no lineage differs in outcome when no figure is large", jo(out, "report_extras.json")["m1a_bracket_second_reading_lineages_whose_outcome_differs"] == [])
    # two bracketed variants of one name in one seed, section, lineage and level: stop (rates cannot be summed without double counting)
    e = m1a_env("br4", {s: {"echo[a]": 0.1, "echo[b]": 0.1} for s in SEEDS})
    code, err, so, out = e.run()
    check("R-56: two bracketed variants of one name in one seed, section, lineage and level stop with exit 3, naming unit and lineage, no figure file", code == 3 and "unit=M1a" in err and "lineage=M1.ages_r3" in err and not os.path.exists(out), (code, err))
    e = m1a_env("br5", {s: {"echo[a]": 0.1, "echo": 0.1} for s in SEEDS})
    code, err, so, out = e.run()
    check("R-56: a bracketed key next to the bare name also stops", code == 3, (code, err))
    # M1b/c: not applied
    e = Env("br6")
    lid = "M1.ages_r3"
    e.surv = {"M1": [lid]}
    e.unit("M1b", "M1", 4000, [{"form": "m1_results", "file": "out.json", "id_map": {lid: lid}, "must_contain": [lid]}])
    for s in SEEDS:
        sc.m1_results_file(e.d("M1b", s), {lid: {"*": sc.m1_level(4000, 0.02, {"foo[bar]": 0.01})}})
    code, err, so, out = e.run()
    T = table(out)
    check("R-56 applies to M1a only: an M1b bracketed key is read as written and has no stripped row", code == 0 and find(T, unit="M1b", rule="foo[bar]") and not find(T, unit="M1b", rule="foo"), code)


def t_shape_rates():
    e = Env("shaperates")
    lid, l2 = "R2.crt_smallest", "C1.cond_chain_f3"
    e.surv = {"R2": [lid], "C1": [l2]}
    e.unit("R2a", "R2", 4000, [sc.r2_spec("r2a", "r2a.json", [lid])])
    s5 = {"form": "c1_s5", "file": "s5.json", "id_map": {l2: l2}, "must_contain": [l2]}
    a3 = {"form": "c1_a3", "run_log": "a3/run_log.json", "must_contain": [l2], "per_survivor": {l2: {"primary_file": "a3/c__own.json", "primary_key": l2, "fallback_file": None, "fallback_key": None, "run_log_key": l2}}}
    bat = {"form": "c1_battery", "file": "battery.json", "id_map": {l2: l2}, "must_contain": [l2]}
    e.unit("C1a", "C1", 2000, [s5, a3])
    e.unit("C1b", "C1", 2000, [bat])
    for s in SEEDS:
        sc.r2_file(e.d("R2a", s), "r2a.json", {lid: {"*": {"s1": (2000, "number", {"zz": (100, 2000)}), "s2": (2000, "number", {"zz": (200, 2000)})}}})
        jdump(e.d("C1a", s) + "/s5.json", {l2: {str(v): sc.s5_level(2000, None, {"sh|S.small": {"rate_in_shape": 0.05, "share_of_level": 0.05, "n_shape": 2000}, "sh|MF_in_shape_cv": {"rate_in_shape": 0.9, "n_shape": 2000}}) for v in L7}})
        jdump(e.d("C1a", s) + "/a3/c__own.json", {l2: {str(v): {"n": 2000, "MF_cv": 0.05, "MF_printform_cv": 0.05, "MF_shape_cv": 0.05, "BEST_generic_cv": 0.05, "BEST_generic_chosen": [], "oracle_any_literal": 0.9, "shapes": {}, "distinct_keys": 1,
                                                       "S": {"x|S.r": {"hit": 10, "applies": 2000, "n_shape": 2000, "rate_in_shape": 0.8, "ci": [0, 1], "share_of_level": 1.0, "mf_in_shape_cv": 0.9}}} for v in L7}})
        jdump(e.d("C1a", s) + "/a3/run_log.json", {l2: {"alias": "a", "alias_err": "", "alias_rc": 0, "own_err": "", "own_rc": 0}})
        jdump(e.d("C1b", s) + "/battery.json", {l2: {str(v): {"n": 2000, "MF_cv": 0.05, "MF_shape_cv": {"x": 0.07}, "BEST_generic_cv": 0.05, "BEST_generic_chosen": [], "best_generic_in_shape": {}, "oracle_any_literal": 0.9, "shapes": {"x": 2000}, "distinct_keys": 1,
                                                       "retries": 0, "S": {"x|S.r": {"hit": 10, "n_shape": 2000, "rate": 0.85}}} for v in L7}})
    code, err, so, out = e.run()
    check("R-57: exit 0", code == 0, err)
    T = table(out)
    ex = jo(out, "report_extras.json")
    R = ex["rates_within_one_shape_reported_only"]
    r2 = [x for x in R if x["unit"] == "R2a" and x["rule"] == "zz" and x["level"] == 1]
    check("R-57: R2 per-shape counts and rates are reported (both shapes, each seed)", sorted(x["shape"] for x in r2) == ["s1", "s2"] and r2[0]["by_seed"]["1"]["k_over_n"] == "1/20" and r2[1]["by_seed"]["2"]["k"] == "200/1", r2)
    find_ = lambda **kw: [x for x in R if all(x.get(k) == v for k, v in kw.items())]
    check("R-57: C1 s5 rate_in_shape of a rule and of MF_in_shape_cv are reported", find_(source="s5", rule="S.small") and find_(source="s5", rule="MF_in_shape_cv")[0]["by_seed"]["1"]["rate_in_shape"] == "9/10", find_(source="s5")[:2])
    check("R-57: C1 a3 rate_in_shape and mf_in_shape_cv are reported", find_(source="a3", rule="S.r")[0]["by_seed"]["2"] == {"mf_in_shape_cv": "9/10", "n_shape": "2000/1", "rate_in_shape": "4/5"}, find_(source="a3"))
    check("R-57: C1 battery S rate and the per-shape MF_shape_cv are reported", find_(source="battery", rule="S.r") and find_(source="battery", rule="MF_shape_cv")[0]["by_seed"]["1"]["rate_in_shape"] == "7/100")
    check("R-57: they enter no decision (0.9, 0.8, 0.85 in-shape rates drop nothing) and MF_in_shape_cv is still not a row of the table", jo(out, "dropped.json") == [] and not find(T, rule="MF_in_shape_cv"))
    check("R-57: oracle_any_literal and best_generic_in_shape stay unread and unreported", not any(x["rule"] in ("oracle_any_literal", "best_generic_in_shape") for x in R))


def t_hashes_and_exclusions():
    e = Env("hashes")
    la = "R1.compass_turns"
    e.surv = {"R1": [la]}
    e.unit("R1a", "R1", 3000, [sc.r1_spec([la])])
    for s in SEEDS:
        sc.quiet_r1(e.d("R1a", s), la)
    e.dry_excl = [{"unit": "R1c", "lineages": ["R1.something"], "error": "x", "confirmed_by": "y"}]
    code, err, so, out = e.run()
    check("R-58: dry_run_exclusions of the plan are copied into report_extras.json", code == 0 and jo(out, "report_extras.json")["dry_run_exclusions"] == e.dry_excl, (code, err))
    # wrong expected hashes: exit 4 for plan, field table, amendment list
    import contextlib
    import io
    for which in ("plan", "field-table", "amendment"):
        e2 = Env("hash_" + which)
        e2.surv = {"R1": [la]}
        e2.unit("R1a", "R1", 3000, [sc.r1_spec([la])])
        for s in SEEDS:
            sc.quiet_r1(e2.d("R1a", s), la)
        p, sp2, ap2 = e2.build()
        good = {"plan": sc.hashlib.sha256(open(p, "rb").read()).hexdigest(), "field-table": sc.hashlib.sha256(open(sc.FIELD_TABLE, "rb").read()).hexdigest(), "amendment": sc.hashlib.sha256(open(ap2, "rb").read()).hexdigest()}
        good[which] = "0" * 64
        er = io.StringIO()
        with contextlib.redirect_stderr(er), contextlib.redirect_stdout(io.StringIO()):
            code = sc.pf.main(["--plan", p, "--survivors", sp2, "--class-table", sc.CLASS_TABLE, "--amendments", ap2, "--field-table", sc.FIELD_TABLE, "--out", os.path.join(e2.root, "out"),
                               "--expect-plan-sha256", good["plan"], "--expect-field-table-sha256", good["field-table"], "--expect-amendment-sha256", good["amendment"]])
        check(f"R-58: a wrong expected SHA-256 of the {which} is refused with exit 4 and nothing is written", code == 4 and "SHA-256" in er.getvalue() and not os.path.exists(os.path.join(e2.root, "out")), (code, er.getvalue()))


def main():
    for t in (t_bracket, t_shape_rates, t_hashes_and_exclusions):
        try:
            t()
        except Exception as ex:
            import traceback
            sc.FAIL += 1
            print("FAIL", t.__name__, "raised", repr(ex))
            traceback.print_exc()
    print(f"RESULT pass={sc.PASS} fail={sc.FAIL} run_dir={sc.ROOT}")
    return 1 if sc.FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
