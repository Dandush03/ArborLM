"""Implementer's self-check of pool_fresh.py on MADE-UP outputs (tiny, written by hand here). Not an independent review.
python3 -I selfcheck_pool.py  -> prints one line per check and a count. Writes only under m0_fr_pool_impl_20261126/runs/<timestamp>/."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import sys
import time
from fractions import Fraction

HERE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "studies", "m0", "fresh_run")
SCR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC_WT = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1"
CLASS_TABLE = SPEC_WT + "/docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/addendum1_rev7_uncounted_rules.json"
FIELD_TABLE = os.path.join(HERE, "field_table.json")
spec = importlib.util.spec_from_file_location("pool_fresh", os.path.join(HERE, "pool_fresh.py"))
pf = importlib.util.module_from_spec(spec)
sys.modules["pool_fresh"] = pf
spec.loader.exec_module(pf)

RUN_ID = time.strftime("%Y%m%d-%H%M%S")
ROOT = os.path.join(SCR, "runs", RUN_ID)
PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("PASS", name)
    else:
        FAIL += 1
        print("FAIL", name, detail)


def jdump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "x") as f:
        json.dump(obj, f)


def wlines(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "x") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


class Env:
    def __init__(self, name):
        self.root = os.path.join(ROOT, name)
        self.units = {}
        self.surv = {}
        self.name = name

    def unit(self, unit, ev, items, outputs):
        self.units[unit] = {"evaluation": ev, "items_per_level": {"dry": 20, "run": items}, "outputs": outputs}

    def d(self, unit, seed):
        return os.path.join(self.root, unit, "seed" + str(seed))

    dry_excl = None

    def build(self, amend=None):
        sp = os.path.join(self.root, "survivors.json")
        jdump(sp, {"evaluations": self.surv})
        plan = {"survivor_list": {"sha256": hashlib.sha256(open(sp, "rb").read()).hexdigest()}, "unit_order": [u for u in pf.UNIT_ORDER if u in self.units], "dry_run_exclusions": self.dry_excl or [],
                "units": {u: {**v, "runs": {s: {"output_dir": self.d(u, s)} for s in ("1", "2", "3", "dry")}} for u, v in self.units.items()}}
        pp = os.path.join(self.root, "plan.json")
        jdump(pp, plan)
        ap = os.path.join(self.root, "amend.json")
        jdump(ap, {"commit": "x", "entries": amend or []})
        return pp, sp, ap

    def run(self, seed_set="run", amend=None, class_table=None, field_table=None, extra=()):
        pp, sp, ap = self.build(amend)
        out = os.path.join(self.root, "out")
        err, so = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(so):
            sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
            expect = ["--expect-plan-sha256", sha(pp), "--expect-field-table-sha256", sha(field_table or FIELD_TABLE), "--expect-amendment-sha256", sha(ap)]
            code = pf.main(["--plan", pp, "--survivors", sp, "--class-table", class_table or CLASS_TABLE, "--amendments", ap, "--field-table", field_table or FIELD_TABLE,
                            "--out", out, "--seed-set", seed_set, *expect, *extra])
        return code, err.getvalue(), so.getvalue(), out


def table(out):
    return json.load(open(os.path.join(out, "pooled_table.json")))


def find(rows, **kw):
    return [r for r in rows if all(r.get(k) == v for k, v in kw.items())]


def jo(out, name):
    return json.load(open(os.path.join(out, name)))


def F(x):
    n, _, d = x["fraction"].partition("/")
    return Fraction(int(n), int(d))


SEEDS = ("1", "2", "3")
L7 = range(7)

# ---------------------------------------------------------------- writers of made-up outputs


def r1_row(lid, lv, h, n=3000, eff=0.01, anti=0.01, fired=100, acc=0.5, mode=None):
    r = {"lineage": lid, "level": lv, "heuristic": h, "n": n, "chance": 0.5, "fired": fired, "acc_fired": acc, "eff": eff, "anti": anti}
    if mode is not None:
        r["mode_rate"] = mode
    return r


def r1_files(d, lid, rules, kinds=("aud", "impl", "feat")):
    """rules: {kind: {name: f(level) -> dict of overrides}}"""
    for kind in kinds:
        rows = []
        for name, f in rules.get(kind, {}).items():
            for lv in L7:
                rows.append(r1_row(lid, lv, name, **(f(lv) if callable(f) else f)))
        wlines(os.path.join(d, f"{lid}.{kind}.jsonl"), rows)


def r1_spec(lids, extra_map=None, feat_lids=()):
    idm = {x: x for x in lids}
    idm.update(extra_map or {})
    return {"form": "r1_rows", "id_map": idm, "kinds": {"aud": {"glob": "*.aud.jsonl", "must_contain": list(lids)}, "impl": {"glob": "*.impl.jsonl", "must_contain": list(lids)},
                                                          "feat": {"glob": "*.feat.jsonl", "must_contain": list(feat_lids)}}}


def quiet_r1(d, lid, aud=None, impl=None, feat=None):
    r1_files(d, lid, {"aud": {"quiet_a": {}, **(aud or {})}, "impl": {"quiet_i": {}, **(impl or {})}, "feat": feat or {}})


def r2_spec(variant, fname, lids, extra_map=None):
    idm = {x: x for x in lids}
    idm.update(extra_map or {})
    return {"form": "r2_json", "variant": variant, "file": fname, "id_map": idm, "must_contain": list(lids)}


def r2_file(d, fname, lineages, with_top=True):
    """lineages: {lid: {level: {shape: (n, answer_type, {rule: (k, napp)})}}}; levels not given are filled with an empty quiet shape."""
    out = {}
    for lid, lvs in lineages.items():
        out[lid] = {}
        for lv in L7:
            shapes = lvs.get(lv, lvs.get("*", {"s": (4000, "number", {"quiet": (10, 4000)})}))
            out[lid][str(lv)] = {sh: {"n": n, "answer_type": at, "distinct_answers": 5, "rules": {rn: {"k": k, "napp": na, "nerr": 0} for rn, (k, na) in rl.items()}} for sh, (n, at, rl) in shapes.items()}
    jdump(os.path.join(d, fname), {"n": 4000, "seeds": "x", "lineages": out})


def m1_level(n, base, rates, extra=None):
    r = {"N": n, "base": base, "rates": rates, "minus_base": {k: 0.0 for k in rates}, "within_applicable": {}, "a3_skipped_items": 0}
    r.update(extra or {})
    return r


def m1_results_file(d, lineages, over=None):
    res = {}
    for lid, lvs in lineages.items():
        res[lid] = {str(lv): lvs.get(lv, lvs.get("*")) for lv in L7}
    jdump(os.path.join(d, "out.json"), {"mode": "fresh", "N": 4000, "seed": 1, "label": "x", "results": res})


def s5_level(n, over=None, rules=None):
    r = {"n": n, "parse_fail": 0, "shapes": {"sh": n}, "distinct_keys": 5, "MF": 0.05, "MFsh": 0.05, "EFF_S": 0.05, "EFF_SM": 0.05, "EFF_F": 0.05, "rules": rules or {}}
    r.update(over or {})
    return r


def c1_outputs(d, lineages, s5=None, bat=None, a3=None):
    pass


# ================================================================ the checks
def t_threshold_and_drop():
    e = Env("threshold")
    lid = "R2.crt_smallest"
    e.surv = {"R2": [lid]}
    e.unit("R2a", "R2", 4000, [r2_spec("r2a", "r2a.json", [lid])])
    for i, s in enumerate(SEEDS):
        ks = {1: [600, 600, 600], 2: [600, 600, 601]}  # level 1: exactly 0.15 pooled; level 2: just above
        lv = {1: {"s": (4000, "number", {"zz open rule": (ks[1][i], 4000)})}, 2: {"s": (4000, "number", {"zz open rule": (ks[2][i], 4000)})},
              3: {"s": (4000, "yn", {"zz yn rule": ([1400, 1400, 1399][i], 4000)})}, 4: {"s": (4000, "yn", {"zz yn rule": ([1400, 1400, 1400][i], 4000)})}}
        r2_file(e.d("R2a", s), "r2a.json", {lid: lv})
    code, err, so, out = e.run()
    check("exit 0 and nothing printed but file names", code == 0 and all(x.startswith("wrote ") for x in so.strip().split("\n")), (code, err, so[:200]))
    T = table(out)
    a = find(T, lineage=lid, level=1, rule="zz open rule")[0]
    check("a figure exactly at 0.15 is not over the bound", F(a["excess"]) == Fraction(15, 100) and not a["over_bound"] and a["abs_excess_plus_uncertainty"]["fraction"] == "3/20", a)
    b = find(T, lineage=lid, level=2, rule="zz open rule")[0]
    check("a figure just above 0.15 (1801/12000) is over the bound", F(b["excess"]) == Fraction(1801, 12000) and b["over_bound"], b)
    c = find(T, lineage=lid, level=3, rule="zz yn rule")[0]
    check("yes/no: 4199/12000 against the base 1/2 is just below -0.15 and over the bound", F(c["excess"]) == Fraction(4199, 12000) - Fraction(1, 2) and c["over_bound"] and c["reading"] == "k_over_napp", c)
    d_ = find(T, lineage=lid, level=4, rule="zz yn rule")[0]
    check("yes/no at exactly 0.35 pooled (-0.15) is not over the bound", F(d_["excess"]) == Fraction(-15, 100) and not d_["over_bound"], d_)
    dr = jo(out, "dropped.json")
    check("dropped.json lists the lineage once with its reason", len(dr) == 1 and dr[0]["lineage"] == lid and len(dr[0]["all_rows_over_the_bound"]) == 2, dr)
    pl = jo(out, "per_lineage.json")[lid]
    check("per_lineage gives the largest counted |excess| per level", pl["levels"]["2"]["rule"] == "zz open rule" and pl["levels"]["3"]["unit"] == "R2a" and pl["dropped"], pl["levels"]["2"])
    ex = jo(out, "report_extras.json")
    check("counts before and after per evaluation", ex["lineages_before_and_after_per_evaluation"]["R2"] == {"before": 1, "dropped": 1, "after": 0}, ex["lineages_before_and_after_per_evaluation"])


def t_rounding():
    e = Env("rounding")
    la, lb, lc = "R1.compass_turns", "R1.boolean_lights_r4", "R1.knights_knaves_r6"
    e.surv = {"R1": [la, lb, lc]}
    e.unit("R1a", "R1", 3000, [r1_spec([la, lb, lc])])
    for s in SEEDS:
        quiet_r1(e.d("R1a", s), la, aud={"edge_above": lambda lv: {"eff": 0.1499 if lv == 2 else 0.01}})
        quiet_r1(e.d("R1a", s), lb, aud={"edge_at": lambda lv: {"eff": 0.15 if lv == 2 else 0.01}})
        quiet_r1(e.d("R1a", s), lc, aud={"neg": lambda lv: {"eff": -0.1500 if lv == 3 else 0.01}, "anti_big": lambda lv: {"anti": 0.2 if lv == 4 else 0.01}})
    code, err, so, out = e.run()
    T = table(out)
    a = find(T, lineage=la, level=2, rule="edge_above", reading="eff")[0]
    check("R1 0.1499 written at 4 decimals: 0.1499 + 0.00005 is not over the bound", F(a["abs_excess_plus_uncertainty"]) == Fraction(14995, 100000) and not a["over_bound"], a)
    b = find(T, lineage=lb, level=2, rule="edge_at", reading="eff")[0]
    check("R1 0.15 written at 4 decimals: within half a unit of the bound, dropped", F(b["abs_excess_plus_uncertainty"]) == Fraction(15005, 100000) and b["over_bound"], b)
    c = find(T, lineage=lc, level=3, rule="neg", reading="eff")[0]
    check("R1 -0.1500: |excess| + 0.00005 is over the bound (two-sided)", c["over_bound"] and F(c["excess"]) == Fraction(-15, 100), c)
    d = find(T, lineage=lc, level=4, rule="anti_big", reading="anti")[0]
    check("R1 anti is read as an excess of its own and decides", d["over_bound"] and F(d["excess"]) == Fraction(2, 10), d)
    dr = {x["lineage"] for x in jo(out, "dropped.json")}
    check("dropped: the two rounded-edge lineages and the anti one, not the 0.1499 one", dr == {lb, lc}, dr)


def t_one_seed_and_classes():
    e = Env("classes")
    lid = "R2.min_heap_ops"
    l2 = "R2.crt_smallest"
    l3 = "R2.count_divisible"
    e.surv = {"R2": [lid, l2, l3]}
    e.unit("R2a", "R2", 4000, [r2_spec("r2a", "r2a.json", [lid, l2, l3])])
    e.unit("R2b", "R2", 4000, [r2_spec("f_rules", "f_rules.json", [lid, l2]), r2_spec("f_rules_new", "f_rules_new.json", [l2, l3])])
    SD = "[a3] removal by deleting the minimum and keeping the order of the rest"
    for i, s in enumerate(SEEDS):
        one = {"named only in seed 1": (1500, 4000)} if i == 0 else {}
        # min_heap_ops: shapes removals=0 (artifact), 1, 2
        mh = {"*": {"removals=0": (1300, "list", {SD: (1170, 1300)}), "removals=1": (1300, "list", {SD: (65, 1300)}), "removals=2": (1400, "list", {SD: (70, 1400)})}}
        r2_file(e.d("R2a", s), "r2a.json", {lid: mh, l2: {"*": {"s": (4000, "number", {**one, "[a3] ignore reverses": (3600, 4000), "(P misread": (3600, 4000), "[a3] only the first rule": (3600, 4000) if True else (0, 0)})}},
                                            l3: {"*": {"s": (4000, "number", {"letter pairs x": (3600, 4000)})}}})
        r2_file(e.d("R2b", s), "f_rules.json", {lid: mh, l2: {"*": {"s": (4000, "number", {"[a3] digits read right to left now": (3600, 4000), "plain digit sum x": (3600, 4000), "scanning only primes up to 61 x": (3600, 4000), "t mod 10 applications": (3600, 4000)})}}})
        r2_file(e.d("R2b", s), "f_rules_new.json", {l2: {"*": {"s": (4000, "number", {"[NEW] (partial) largest modulus: try r, r+m, r+2m against the other congruences, else r": (3600, 4000)})}},
                                                    l3: {"*": {"s": (4000, "number", {"[NEW] (P) misread: each distinct value counted once (the wording now excludes it)": (3600, 4000)})}}})
    code, err, so, out = e.run()
    T = table(out)
    a = find(T, unit="R2a", lineage=l2, level=3, rule="named only in seed 1")[0]
    check("a rule named for one seed only counts no hit and the other seeds' items (1500/12000)", a["pooled_figure"]["fraction"] == "1/8" and a["items"] == 12000 and a["named_in_seeds"] == ["1"] and not a["over_bound"], a)
    for nm, u, lineage, why in [("[a3] ignore reverses", "R2a", l2, "artifact"), ("(P misread", "R2a", l2, "P"), ("letter pairs x", "R2a", l3, "partial"), ("plain digit sum x", "R2b", l2, "partial"),
                                ("[a3] digits read right to left now", "R2b", l2, "P (starts with)")]:
        r = find(T, unit=u, lineage=lineage, level=3, rule=nm)[0]
        check(f"R2 {why} rule is uncounted with its entry", not r["counted"] and r["class_entry"] and not r["over_bound"], r)
    r = find(T, unit="R2a", lineage=l2, level=0, rule="[a3] only the first rule")[0]
    check("R2 level-dependent artifact: uncounted at level 0 (rule applied in order)", not r["counted"] and "artifact" in r["class_entry"], r)
    r = find(T, unit="R2a", lineage=l2, level=1, rule="[a3] only the first rule")[0]
    check("R2 level-dependent artifact: counted from level 1, and over the bound", r["counted"] and r["over_bound"], r)
    r = find(T, unit="R2b", lineage=l2, level=3, rule="t mod 10 applications")[0]
    check("R2 'construct' reaches no entry and counts", r["counted"] and r["over_bound"], r)
    r = find(T, unit="R2b", lineage=l2, level=3, rule="[NEW] (partial) largest modulus: try r, r+m, r+2m against the other congruences, else r")[0]
    check("[NEW] rule: an entry for crt_smallest is uncounted", not r["counted"], r)
    r = find(T, unit="R2b", lineage=l3, level=3, rule="[NEW] (P) misread: each distinct value counted once (the wording now excludes it)")[0]
    check("[NEW] rule: an entry for count_divisible is uncounted", not r["counted"], r)
    # shape-dependent
    rs = find(T, unit="R2a", lineage=lid, level=3, rule=SD)
    byshape = {x["shape"]: x for x in rs}
    check("shape-dependent rule: read per shape, removals=0 uncounted and 1, 2 counted", sorted(byshape) == ["removals=0", "removals=1", "removals=2"] and not byshape["removals=0"]["counted"]
          and byshape["removals=1"]["counted"] and byshape["removals=2"]["counted"], [(x["shape"], x["counted"]) for x in rs])
    check("shape-dependent rule: the uncounted shape's 0.9 does not drop it and is not pooled into the others", not any(x["over_bound"] for x in rs) and F(byshape["removals=1"]["pooled_figure"]) == Fraction(65, 1300), byshape["removals=1"]["pooled_figure"])
    names = {x["lineage"] for x in jo(out, "dropped.json")}
    check("dropped lineages are exactly the ones with a counted rule over the bound", names == {l2}, names)
    uc = [x for x in jo(out, "report_extras.json")["uncounted_rules"] if x["rule"] == SD]
    check("report lists the uncounted shape with its entry", uc and uc[0]["shape"] == "removals=0" and "shape equal" in uc[0]["entry"], uc)


def t_shape_dependent_variants():
    SD = "[a3] removal by deleting the minimum and keeping the order of the rest"
    lid = "R2.min_heap_ops"
    # (1) per-shape counts: shape 1 itself above the bound while the pooled-over-shapes figure would be below
    e = Env("shapedep1")
    e.surv = {"R2": [lid]}
    e.unit("R2a", "R2", 4000, [r2_spec("r2a", "r2a.json", [lid])])
    for s in SEEDS:
        r2_file(e.d("R2a", s), "r2a.json", {lid: {"*": {"removals=0": (1300, "list", {SD: (0, 1300)}), "removals=1": (1300, "list", {SD: (260, 1300)}), "removals=2": (1400, "list", {SD: (0, 1400)})}}})
    code, err, so, out = e.run()
    T = table(out)
    r = find(T, rule=SD, shape="removals=1", level=3)[0]
    check("shape-dependent, per-shape counts: shape removals=1 at 0.2 on its own items drops (pooled over shapes it would be 0.0650)", r["over_bound"] and F(r["excess"]) == Fraction(1, 5), r)
    # (2) counts only summed over shapes of both classes: the rule counts on that figure
    e = Env("shapedep2")
    e.surv = {"R2": [lid]}
    e.unit("R2a", "R2", 4000, [r2_spec("r2a", "r2a.json", [lid])])
    for s in SEEDS:
        r2_file(e.d("R2a", s), "r2a.json", {lid: {"*": {"removals=0..2 summed": (4000, "list", {SD: (3000, 4000)})}}})
    code, err, so, out = e.run()
    T = table(out)
    r = find(T, rule=SD, level=3)[0]
    check("shape-dependent, counts only summed over shapes: the rule counts on that figure", r["counted"] and r["over_bound"] and r["shape"] == "removals=0..2 summed", r)


def t_cond():
    lid = "R2.expression_eval"
    e = Env("cond")
    e.surv = {"R2": [lid]}
    e.unit("R2a", "R2", 4000, [r2_spec("r2a", "r2a.json", [lid])])
    for s in SEEDS:
        r2_file(e.d("R2a", s), "r2a.json", {lid: {"*": {"s": (4000, "number", {"zz [cond] rule": (400, 2000), "zz plain": (400, 2000)})}}})
    code, err, so, out = e.run()
    T = table(out)
    rd = {x["reading"]: x for x in find(T, rule="zz [cond] rule", level=2)}
    check("[cond] rule has both readings: k/n = 0.1 (under) and k/napp = 0.2 (over); the larger decides", sorted(rd) == ["k_over_n", "k_over_napp"] and not rd["k_over_n"]["over_bound"] and rd["k_over_napp"]["over_bound"]
          and F(rd["k_over_n"]["pooled_figure"]) == Fraction(1, 10) and F(rd["k_over_napp"]["pooled_figure"]) == Fraction(1, 5) and rd["k_over_napp"]["items"] == 6000, rd)
    pl = find(T, rule="zz plain", level=2)
    check("a rule without [cond] has the k/n figure only", [x["reading"] for x in pl] == ["k_over_n"], pl)
    check("the lineage is dropped on the k/napp figure", [x["lineage"] for x in jo(out, "dropped.json")] == [lid])


def t_nonsurvivor_alias_missing_stop():
    # a lineage that is not on the survivor list; a lineage under an alias id; a survivor missing from one unit
    e = Env("alias")
    la, lb = "C1.fast_power_f4", "C1.binary_search_f3"
    e.surv = {"C1": [la, lb]}
    s5spec = {"form": "c1_s5", "file": "s5.json", "id_map": {"C1.fast_power_f3": la, "C1.binary_search_f3": lb}, "must_contain": [la, lb]}
    a3spec = {"form": "c1_a3", "run_log": "a3/run_log.json", "must_contain": [la, lb], "per_survivor": {
        la: {"primary_file": "a3/fast_power_f3__alias.json", "primary_key": "C1.fast_power_r2", "fallback_file": "a3/fast_power_f3__own.json", "fallback_key": "C1.fast_power_f3", "run_log_key": "C1.fast_power_f3"},
        lb: {"primary_file": "a3/binary_search_f3__alias.json", "primary_key": "C1.binary_search", "fallback_file": "a3/binary_search_f3__own.json", "fallback_key": "C1.binary_search_f3", "run_log_key": "C1.binary_search_f3"}}}
    e.unit("C1a", "C1", 2000, [s5spec, a3spec])
    for s in SEEDS:
        d = e.d("C1a", s)
        jdump(d + "/s5.json", {"C1.fast_power_f3": {str(v): s5_level(2000) for v in L7}, "C1.binary_search_f3": {str(v): s5_level(2000) for v in L7},
                               "C1.not_a_survivor_f3": {str(v): s5_level(2000, {"MF": 0.9}) for v in L7}})
        a3lv = lambda: {str(v): {"n": 2000, "MF_cv": 0.05, "MF_printform_cv": 0.05, "MF_shape_cv": 0.05, "BEST_generic_cv": 0.05, "BEST_generic_chosen": ["a", "b"], "oracle_any_literal": 0.9,
                                  "shapes": {"x": 2000}, "S": {"x|S.rule": {"hit": 10, "applies": 2000, "n_shape": 2000, "rate_in_shape": 0.005, "ci": [0.0, 0.1], "share_of_level": 1.0, "mf_in_shape_cv": 0.1}}, "distinct_keys": 3} for v in L7}
        jdump(d + "/a3/fast_power_f3__alias.json", {"C1.fast_power_r2": a3lv()})
        jdump(d + "/a3/binary_search_f3__alias.json", {"C1.binary_search": a3lv()})
        jdump(d + "/a3/run_log.json", {"C1.fast_power_f3": {"alias": "x", "alias_err": "", "alias_rc": 0, "own_err": "", "own_rc": None}, "C1.binary_search_f3": {"alias": "x", "alias_err": "", "alias_rc": 0, "own_err": "", "own_rc": None}})
    code, err, so, out = e.run()
    T = table(out)
    check("a lineage written under an alias id is read under its survivor id (s5 and a3)", find(T, unit="C1a", lineage=la, source="s5", rule="MF", level=0) and find(T, unit="C1a", lineage=la, source="a3", rule="MF_cv", level=0), code)
    check("a lineage that is not on the survivor list is not read (its 0.9 drops nothing)", not any(r["lineage"] == "C1.not_a_survivor_f3" for r in T) and jo(out, "dropped.json") == [], jo(out, "dropped.json"))
    check("R-46: oracle_any_literal (0.9, not read) is not a row and drops nothing", not find(T, rule="oracle_any_literal") and jo(out, "dropped.json") == [])
    # the survivor missing from one unit's output: STOP
    e = Env("missing")
    la, lb = "R1.compass_turns", "R1.knights_knaves_r6"
    e.surv = {"R1": [la, lb]}
    e.unit("R1a", "R1", 3000, [r1_spec([la, lb])])
    e.unit("R1b", "R1", 3000, [r1_spec([la, lb])])
    for s in SEEDS:
        quiet_r1(e.d("R1a", s), la)
        quiet_r1(e.d("R1a", s), lb)
        quiet_r1(e.d("R1b", s), la)
        if s != "3":
            quiet_r1(e.d("R1b", s), lb)
        else:
            quiet_r1(e.d("R1b", s), "R1.other")  # lb has no file in seed 3
    code, err, so, out = e.run()
    check("a survivor missing from one unit's output (one seed): exit 3, only unit and lineage named, no figure file", code == 3 and "unit=R1b" in err and f"lineage={lb}" in err and not os.path.exists(out), (code, err))
    # a lineage with no row at one level
    e = Env("missing_level")
    e.surv = {"R1": [la]}
    e.unit("R1a", "R1", 3000, [r1_spec([la])])
    for s in SEEDS:
        rows = [r1_row(la, lv, "quiet_a") for lv in L7 if not (s == "2" and lv == 5)]
        wlines(e.d("R1a", s) + f"/{la}.aud.jsonl", rows)
        wlines(e.d("R1a", s) + f"/{la}.impl.jsonl", [r1_row(la, lv, "q") for lv in L7])
        wlines(e.d("R1a", s) + f"/{la}.feat.jsonl", [])
    code, err, so, out = e.run()
    check("a lineage with no row at one level of one seed also stops", code == 3 and "unit=R1a" in err, (code, err))


def t_r1_exact_and_amendment_and_feat():
    e = Env("exact")
    la, lb = "R1.compass_turns", "R1.boolean_lights_r4"
    e.surv = {"R1": [la, lb]}
    e.unit("R1a", "R1", 3000, [r1_spec([la, lb], extra_map={"R1.alias_of_boolean_lights": lb}, feat_lids=[lb])])
    ex = {"n": 3000, "fired": 3000, "acc": 1.0}
    for s in SEEDS:
        d = e.d("R1a", s)
        # compass_turns: 'chebyshev' is an M entry (every R1 lineage) and exact; 'ccw_as_cw' is an EXCL entry for compass_turns only; 'exact_not_entry' is exact and not an entry
        r1_files(d, la, {"aud": {"quiet_a": {}, "chebyshev": {**ex, "eff": 0.5, "anti": 0.0}, "a4:ccw_as_cw": {"eff": 0.4, "anti": 0.0}, "exact_not_entry": {**ex, "eff": 0.5, "anti": 0.0}}, "impl": {"q": {}}, "feat": {}})
        # boolean_lights: the same two names; 'ccw_as_cw' is not an entry for this lineage, so it counts; the row's lineage field is an alias id
        rows = [r1_row("R1.alias_of_boolean_lights", lv, "ccw_as_cw", eff=0.2 if lv == 1 else 0.01) for lv in L7] + [r1_row("R1.alias_of_boolean_lights", lv, "quiet_a") for lv in L7]
        wlines(d + f"/{lb}.aud.jsonl", rows)
        wlines(d + f"/{lb}.impl.jsonl", [r1_row(lb, lv, "q") for lv in L7])
        wlines(d + f"/{lb}.feat.jsonl", [{"lineage": lb, "level": lv, "heuristic": "feat:lookup", "eff": 0.01, "anti": None, "acc_fired": None, "fired": 1000, "n": 1000} for lv in L7])
        wlines(d + "/R1.stranger.aud.jsonl", [r1_row("R1.stranger", lv, "x", eff=0.9) for lv in L7])
    code, err, so, out = e.run()
    T = table(out)
    ex_ = jo(out, "report_extras.json")
    rows = {(x["lineage"], x["rule"]): x for x in ex_["r1_exact_rows"]}
    check("an exact R1 rule that is an entry (chebyshev) is listed, an entry and set aside", rows[(la, "chebyshev")]["rule_is_an_entry_of_the_class_table"] and rows[(la, "chebyshev")]["set_aside"], rows.get((la, "chebyshev")))
    check("an exact R1 rule that is not an entry is listed, counts and is not set aside", not rows[(la, "exact_not_entry")]["rule_is_an_entry_of_the_class_table"] and rows[(la, "exact_not_entry")]["counted"] and not rows[(la, "exact_not_entry")]["set_aside"], rows.get((la, "exact_not_entry")))
    ch = find(T, lineage=la, rule="chebyshev", level=2, reading="eff")[0]
    check("the exact entry rule's excess 0.5 drops nothing", not ch["counted"] and not ch["over_bound"], ch)
    en = find(T, lineage=la, rule="a4:ccw_as_cw", level=2, reading="eff")[0]
    check("EXCL entry for compass_turns, matched on the bare name (leading a4: removed)", not en["counted"], en)
    al = find(T, lineage=lb, rule="ccw_as_cw", level=1, reading="eff")[0]
    check("the same name for a lineage the entry does not name counts (alias-id row read under its survivor id)", al["counted"] and al["over_bound"], al)
    drop = {x["lineage"] for x in jo(out, "dropped.json")}
    check("dropped: compass_turns (exact non-entry 0.5) and boolean_lights (ccw_as_cw 0.2)", drop == {la, lb}, drop)
    check("rows of a lineage that is not a survivor are not read", not any(x["lineage"] == "R1.stranger" for x in T) and ex_["rows_not_read"].get("r1_rows_of_non_survivors_not_read", 0) > 0, ex_["rows_not_read"])
    fd = [x for x in ex_["rows_with_an_item_count_other_than_the_plan"] if x["source"] == "feat"]
    check("fitted-lookup rows (1,000 items against the plan's 3,000) are listed as a count other than the plan's", fd and fd[0]["levels"][0]["items"] == 1000, fd[:1])
    ft = find(T, lineage=lb, rule="feat:lookup", level=0, reading="eff")[0]
    check("feat row: items from the output (1000 per seed, 3000 in all), no anti figure", ft["items"] == 3000 and not find(T, lineage=lb, rule="feat:lookup", reading="anti"), ft)
    # amendment list: an entry for one lineage counts only there
    e2 = Env("amend")
    e2.surv = {"R1": [la, lb]}
    e2.unit("R1a", "R1", 3000, [r1_spec([la, lb])])
    for s in SEEDS:
        for lid in (la, lb):
            r1_files(e2.d("R1a", s), lid, {"aud": {"quiet_a": {}, "custom_rule": lambda lv: {"eff": 0.3 if lv == 2 else 0.01}}, "impl": {"q": {}}, "feat": {}})
    code, err, so, out = e2.run(amend=[{"unit": "R1a", "lineage": la, "rule": "custom_rule"}])
    T = table(out)
    a1, a2 = find(T, lineage=la, rule="custom_rule", level=2, reading="eff")[0], find(T, lineage=lb, rule="custom_rule", level=2, reading="eff")[0]
    check("amendment list: uncounted for the lineage it names, counts for the other", not a1["counted"] and a1["class_entry_kind"] == "amendment list" and a2["counted"] and a2["over_bound"], (a1, a2))
    check("amendment: only the other lineage is dropped", [x["lineage"] for x in jo(out, "dropped.json")] == [lb])


def t_m1():
    e = Env("m1")
    lr, lg, lf = "M1.ratio_share_r3", "M1.gcd_lcm_r4", "M1.finite_differences_r4"
    e.surv = {"M1": [lr, lg, lf]}
    e.unit("M1b", "M1", 4000, [{"form": "m1_results", "file": "out.json", "id_map": {x: x for x in (lr, lg, lf)}, "must_contain": [lr, lg, lf]}])
    e.unit("M1a", "M1", 4000, [{"form": "m1_battery", "file": "battery.json", "id_map": {x: x for x in (lr, lg, lf)}, "must_contain": [lr, lg, lf]}])
    for s in SEEDS:
        big = {"im:largest_share": 0.5, "a3:largest_share": 0.5, "foo__within_applicable": 0.9, "plain_rule": 0.01}
        quiet = {"q": 0.01}
        m1_results_file(e.d("M1b", s), {lr: {"*": m1_level(4000, 0.02, big, {"one_op_best": ["a", "b"], "asked_is_largest_observed_vs_uniform": [0.9, 0.3]})},
                                        lg: {"*": m1_level(4000, 0.02, {**quiet, "im:largest_share": 0.5, "foo__within_applicable": 0.9})},
                                        lf: {"*": m1_level(300 if s == "1" else 4000, 0.02, {"im:next_term_only": 0.01, "a3:next_term_only": 0.01})}})
        sec = lambda rates, base=0.02: {lv: {"N": 4000, "base": base, "rates": rates, "minus_base": {k: 0.0 for k in rates}, "mode_insample": 0.9, "answer_echoed_anywhere": 0.9, "halfwidth95": {k: 0.0 for k in rates}} for lv in map(str, L7)}
        a4sec = lambda rates, base=0.02: {lv: {"N": 4000, "base": base, "best_echo": ["a", "b"], "answer_echoed_anywhere": 0.9, "rates": rates, "minus_base": {k: 0.0 for k in rates}, "within_applicable": {}} for lv in map(str, L7)}
        a3sec = lambda rates, base=0.02: {**{lv: {"N": 4000, "base": base, "rates": rates, "minus_base": {k: 0.0 for k in rates}} for lv in map(str, L7)}, "a3_skipped_items": 0}
        jdump(e.d("M1a", s) + "/battery.json", {"n": 4000, "seeds": {"own": 410302, "a4": 17, "a3": 5}, "exclusions": {}, "summary": {},
                                                "raw": {"own": {lr: sec({"largest_share": 0.5}), lg: sec({"largest_share": 0.5}), lf: sec({"q": 0.01})},
                                                        "a4": {lr: a4sec({"im:largest_share": 0.5, "a4:echo_pos": 0.01}), lg: a4sec({"q": 0.01}), lf: a4sec({"q": 0.01})},
                                                        "a3": {lr: a3sec({"largest_share": 0.5}), lg: a3sec({"largest_share": 0.5}), lf: a3sec({"q": 0.01})}}})
    code, err, so, out = e.run()
    T = table(out)
    check("exit 0 for the M1 case", code == 0, err)
    check("M1 key ending __within_applicable is not a rule (no row)", not [r for r in T if r["rule"].endswith("__within_applicable")] and not find(T, unit="M1b", lineage=lr, rule="foo__within_applicable"), None)
    a = find(T, unit="M1b", lineage=lr, rule="im:largest_share", level=1, reading="vs_chance")[0]
    b = find(T, unit="M1b", lineage=lg, rule="im:largest_share", level=1, reading="vs_chance")[0]
    check("M1 pair that is an entry (ratio_share, im:largest_share) is uncounted; the same name for gcd_lcm counts and drops", not a["counted"] and b["counted"] and b["over_bound"], (a, b))
    c = find(T, unit="M1b", lineage=lr, rule="a3:largest_share", level=1, reading="vs_chance")[0]
    check("the audit-3 pair by name and definition (ratio_share) is an entry", not c["counted"], c)
    p = find(T, unit="M1a", lineage=lr, rule="im:largest_share", level=1, reading="vs_chance")
    check("M1a: section own 'largest_share' is named 'im:largest_share' and a4's 'im:largest_share' as written: two rows (two streams), both uncounted", len(p) == 2 and {x["source"] for x in p} == {"own", "a4"} and not any(x["counted"] for x in p), p)
    q = find(T, unit="M1a", lineage=lr, rule="a3:largest_share", level=1, reading="vs_chance")
    check("M1a: section a3 key is prefixed a3:", len(q) == 1 and not q[0]["counted"], q)
    q = find(T, unit="M1a", lineage=lg, rule="im:largest_share", level=1, reading="vs_chance")
    check("M1a: the same prefixed key for another lineage counts and drops", q and q[0]["counted"] and q[0]["over_bound"], q)
    vb = find(T, unit="M1b", lineage=lg, rule="im:largest_share", level=1, reading="vs_base")[0]
    check("M1 is read against base as well: 0.5 - 0.02, with two half-units (5 decimals) of uncertainty", F(vb["excess"]) == Fraction(48, 100) and F(vb["rounding_uncertainty"]) == Fraction(2, 200000), vb)
    vc = find(T, unit="M1b", lineage=lg, rule="im:largest_share", level=1, reading="vs_chance")[0]
    check("M1 against chance has one half-unit", F(vc["rounding_uncertainty"]) == Fraction(1, 200000), vc)
    vm = find(T, unit="M1a", lineage=lf, rule="q", level=1)
    check("M1a (4 decimals): vs_chance half-unit 1/20000", F(find(T, unit="M1a", lineage=lf, rule="a3:q", level=1, reading="vs_chance")[0]["rounding_uncertainty"]) == Fraction(1, 20000), vm)
    bs = find(T, unit="M1b", lineage=lf, rule="base", level=1, reading="vs_chance")
    check("M1 base is read as the rule 'most frequent answer' against chance", len(bs) == 1 and F(bs[0]["pooled_figure"]) == Fraction(2, 100) * 1, bs)
    ex = jo(out, "report_extras.json")
    diffs = [x for x in ex["rows_with_an_item_count_other_than_the_plan"] if x["unit"] == "M1b" and x["lineage"] == lf]
    check("a row with an item count other than the plan's (300) is listed, and its items are taken from the output", diffs and diffs[0]["levels"][0]["items"] == 300 and find(T, unit="M1b", lineage=lf, rule="im:next_term_only", level=0, reading="vs_chance")[0]["items"] == 300 + 4000 + 4000, diffs)
    pc = find(T, unit="M1b", lineage=lf, rule="im:next_term_only", level=0, reading="vs_chance")[0]
    check("im:next_term_only of finite_differences is not an entry (counts)", pc["counted"], pc)
    check("M1 'one_op_best' and 'asked_is_largest_observed_vs_uniform' are not read", not find(T, rule="one_op_best") and not find(T, rule="asked_is_largest_observed_vs_uniform"))
    check("M1a: mode_insample and answer_echoed_anywhere (0.9) are not read", not any("mode_insample" in r["rule"] or "answer_echoed" in r["rule"] for r in T))


def t_c1_eff_and_classes():
    e = Env("c1")
    lid = "C1.cond_chain_f3"
    lid2 = "C1.turtle_walk_f3"
    e.surv = {"C1": [lid, lid2]}
    s5spec = {"form": "c1_s5", "file": "s5.json", "id_map": {lid: lid, lid2: lid2}, "must_contain": [lid, lid2]}
    batspec = {"form": "c1_battery", "file": "battery.json", "id_map": {lid: lid, lid2: lid2}, "must_contain": [lid, lid2]}
    clspec = {"form": "c1_closed", "file": "f5.json", "id_map": {lid: lid}, "must_contain": [lid]}
    a3spec = {"form": "c1_a3", "run_log": "a3/run_log.json", "must_contain": [lid, lid2], "per_survivor": {
        lid: {"primary_file": "a3/c__alias.json", "primary_key": "C1.cond_chain", "fallback_file": "a3/c__own.json", "fallback_key": lid, "run_log_key": lid},
        lid2: {"primary_file": "a3/t__own.json", "primary_key": lid2, "fallback_file": None, "fallback_key": None, "run_log_key": lid2}}}
    e.unit("C1a", "C1", 2000, [s5spec, a3spec])
    e.unit("C1b", "C1", 2000, [batspec])
    e.unit("C1c", "C1", 2000, [s5spec, a3spec, clspec])
    for s in SEEDS:
        for u in ("C1a", "C1c"):
            d = e.d(u, s)
            # lid: EFF_F 0.2 with every single rule below (cond_chain); EFF_SM 0.5 is an entry (uncounted); M.arg_plus_1 0.5 is an a4 entry; M.not_an_entry 0.5 counts (only for lid2)
            r_ok = {"sh|S.small": {"rate_in_shape": 0.05, "share_of_level": 0.05, "n_shape": 2000}, "sh|M.arg_plus_1": {"rate_in_shape": 0.5, "share_of_level": 0.5, "n_shape": 2000},
                    "sh|MF_in_shape_cv": {"rate_in_shape": 0.9, "n_shape": 2000}}
            r_bad = {"sh|M.not_an_entry": {"rate_in_shape": 0.2, "share_of_level": 0.2, "n_shape": 2000}}
            jdump(d + "/s5.json", {lid: {str(v): s5_level(2000, {"EFF_F": 0.2 if v == 3 else 0.05, "EFF_SM": 0.5}, r_ok) for v in L7},
                                   lid2: {str(v): s5_level(2000, None, {**r_bad}) for v in L7}})
            lv = lambda extra=None: {str(v): {"n": 2000, "MF_cv": 0.05, "MF_printform_cv": 0.3 if v == 2 else 0.05, "MF_shape_cv": 0.05, "BEST_generic_cv": 0.05, "BEST_generic_chosen": ["a", "b"],
                                              "oracle_any_literal": 0.9, "shapes": {"x": 2000}, "distinct_keys": 3, "S": {"x|S.no_turns": {"hit": 1000, "applies": 2000, "n_shape": 2000, "rate_in_shape": 0.5, "ci": [0, 1], "share_of_level": 1.0, "mf_in_shape_cv": 0.1},
                                                                                                       "x|S.other": {"hit": 10, "applies": 2000, "n_shape": 2000, "rate_in_shape": 0.005, "ci": [0, 1], "share_of_level": 1.0, "mf_in_shape_cv": 0.1}}} for v in L7}
            jdump(d + "/a3/c__alias.json", {"C1.cond_chain": lv()})
            jdump(d + "/a3/c__own.json", {lid: lv()})
            jdump(d + "/a3/t__own.json", {lid2: lv()})
            jdump(d + "/a3/run_log.json", {lid: {"alias": "a", "alias_err": "AttributeError in a3_shortcuts.py" if (u == "C1c" and s == "2") else "", "alias_rc": 1 if (u == "C1c" and s == "2") else 0, "own_err": "", "own_rc": 0},
                                           lid2: {"alias": "a", "alias_err": "", "alias_rc": 0, "own_err": "", "own_rc": 0}})
        jdump(e.d("C1c", s) + "/f5.json", {lid: {"per_level": {str(v): {"M.no_even_branch": 0.5, "F.pow_res_c0": 0.01} for v in L7}, "n_per_level": {str(v): 2000 for v in L7}, "errors": {}}})
        bl = lambda: {str(v): {"n": 2000, "MF_cv": 0.05, "MF_shape_cv": {"x": 0.05}, "BEST_generic_cv": 0.05, "BEST_generic_chosen": ["a", "b"], "best_generic_in_shape": {"x": {"rule": "r", "rate": 0.9}}, "oracle_any_literal": 0.9,
                                  "shapes": {"x": 2000}, "distinct_keys": 3, "retries": 0, "S": {"x|C.algorithm_rerun": {"hit": 2000, "n_shape": 2000, "rate": 1.0}, "x|S.no_turns": {"hit": 700, "n_shape": 2000, "rate": 0.35}, "RULE_ERROR:KeyError:x|S.boom": {"hit": 1900, "n_shape": 2000, "rate": 0.95}}} for v in L7}
        jdump(e.d("C1b", s) + "/battery.json", {lid: bl(), lid2: bl()})
    code, err, so, out = e.run()
    T = table(out)
    check("exit 0 for the C1 case", code == 0, err)
    g = find(T, unit="C1a", lineage=lid, source="s5", rule="EFF_F", level=3)[0]
    check("EFF_F above the bound with every single rule below: EFF_F counts as written and drops the lineage", g["counted"] and g["over_bound"] and F(g["pooled_figure"]) == Fraction(1, 5), g)
    check("EFF_SM is uncounted by the class table (measure) however large", not find(T, unit="C1a", lineage=lid, source="s5", rule="EFF_SM", level=3)[0]["counted"])
    r = find(T, unit="C1a", lineage=lid, source="s5", rule="M.arg_plus_1", level=1)[0]
    check("a4 'M.arg_plus_1' (partial trace) is uncounted, 0.5 notwithstanding; hits recovered as round(rate_in_shape x n_shape)", not r["counted"] and F(r["pooled_figure"]) == Fraction(1, 2), r)
    r = find(T, unit="C1a", lineage=lid2, source="s5", rule="M.not_an_entry", level=1)[0]
    check("an M.* rule that is not an entry counts (the literal names, not the prefix) and drops", r["counted"] and r["over_bound"], r)
    check("the in-shape rate MF_in_shape_cv is not read", not find(T, rule="MF_in_shape_cv"))
    r = find(T, unit="C1a", lineage=lid, source="a3", rule="S.no_turns", level=1)[0]
    r2 = find(T, unit="C1b", lineage=lid, source="battery", rule="S.no_turns", level=1)[0]
    check("S.no_turns: an entry for the a3 source (uncounted), counted in the battery's output (BATTERY_MUT is a doubt) at 0.35, over the bound", not r["counted"] and r2["counted"] and r2["over_bound"], (r["class_entry"], r2["counted"]))
    check("an error-marker shape (RULE_ERROR:...|rule, 0.95) is not read", not find(T, rule="S.boom") and jo(out, "report_extras.json")["rows_not_read"].get("error_marker_rows_not_read", 0) > 0)
    r = find(T, unit="C1b", lineage=lid, source="battery", rule="C.algorithm_rerun", level=1)[0]
    check("battery C.* control is uncounted (1.0 does not drop)", not r["counted"], r)
    r = find(T, unit="C1c", lineage=lid, source="f5", rule="M.no_even_branch", level=1)[0]
    check("closed-forms M.no_even_branch is an entry of its source", not r["counted"], r)
    r = find(T, unit="C1a", lineage=lid, source="a3", rule="MF_printform_cv", level=2)[0]
    check("R-46: MF_printform_cv counts (0.3, drops); oracle_any_literal and best_generic_in_shape are not read", r["counted"] and r["over_bound"] and not find(T, rule="oracle_any_literal") and not find(T, rule="best_generic_in_shape"), r)
    fb = jo(out, "report_extras.json")["a3_wrapper_fallbacks"]
    check("a3 wrapper fallback read from run_log.json and reported (C1c, seed 2, alias_rc 1)", len(fb) == 1 and fb[0]["unit"] == "C1c" and fb[0]["seed"] == "2" and fb[0]["lineage"] == lid and fb[0]["read_from"] == "a3/c__own.json", fb)
    check("the battery's per-shape MF_shape_cv is recovered to hits and summed (0.05 x 2000 = 100 per level)", F(find(T, unit="C1b", lineage=lid, rule="MF_shape_cv", level=1)[0]["pooled_figure"]) == Fraction(5, 100))
    alt = jo(out, "report_extras.json")["s5_recovery_alternatives_that_change_a_decision"]
    check("s5 alternative recovery list exists (and is empty when share_of_level agrees with rate_in_shape)", alt == [], alt)


def t_r1c_stdout():
    e = Env("r1c")
    la = "R1.compass_turns"
    e.surv = {"R1": [la]}
    e.unit("R1c", "R1", 3000, [{"form": "r1c_stdout", "file": "stdout.txt", "id_map": {la: la}, "must_contain": [la]}])
    long_name = "lookup (asked on at start, #switches wired to it, #presses parity) and more words"
    for s in SEEDS:
        def line(lid, name, eff, anti):
            return f"{lid:36s} {name[:60]:60s} eff " + " ".join(f"{x:+.3f}" for x in eff) + "   anti " + " ".join(f"{x:+.3f}" for x in anti)
        lines = [line(la, "word_turns_only", [0.1, 0.1, 0.150, 0.149, 0.1, 0.1, -0.150], [0.0] * 7), line(la, long_name, [0.0] * 7, [0.0] * 7), "uv: some other line", "R1.stranger_r4 " + "x" * 90]
        os.makedirs(e.d("R1c", s), exist_ok=True)
        with open(e.d("R1c", s) + "/stdout.txt", "x") as f:
            f.write("\n".join(lines) + "\n")
    code, err, so, out = e.run()
    T = table(out)
    check("R1c: exit 0", code == 0, err)
    a = find(T, rule="word_turns_only", level=2, reading="eff")[0]
    b = find(T, rule="word_turns_only", level=3, reading="eff")[0]
    c = find(T, rule="word_turns_only", level=6, reading="eff")[0]
    check("R1c +0.150 printed: with the 0.00055 uncertainty it is over the bound; +0.149 is not (0.14955); -0.150 is over", a["over_bound"] and not b["over_bound"] and c["over_bound"] and F(a["rounding_uncertainty"]) == Fraction(55, 100000), (a, b, c))
    check("R1c: the rule name cut to 60 characters is read as printed; items are the plan's 3000 per seed", find(T, rule=long_name[:60], level=0) and a["items"] == 9000, a)
    check("R1c: an unrelated stdout line is not read", jo(out, "report_extras.json")["rows_not_read"].get("r1c_stdout_lines_not_read") == 3 and not find(T, lineage="R1.stranger_r4"))
    # a line with fewer than 7 values stops
    e = Env("r1c_bad")
    e.surv = {"R1": [la]}
    e.unit("R1c", "R1", 3000, [{"form": "r1c_stdout", "file": "stdout.txt", "id_map": {la: la}, "must_contain": [la]}])
    for s in SEEDS:
        os.makedirs(e.d("R1c", s), exist_ok=True)
        with open(e.d("R1c", s) + "/stdout.txt", "x") as f:
            f.write(f"{la:36s} {'word_turns_only':60s} eff " + " ".join(f"{x:+.3f}" for x in [0.1] * 6) + "   anti " + " ".join(f"{x:+.3f}" for x in [0.1] * 6) + "\n")
    code, err, so, out = e.run()
    check("R1c: a line with 6 values stops (levels cannot be read), naming unit and lineage", code == 3 and "unit=R1c" in err and la in err, (code, err))


def t_misc():
    # dry seed set, same code path; class table hash; unknown field; no overwrite
    e = Env("dry")
    la = "R1.compass_turns"
    e.surv = {"R1": [la]}
    e.unit("R1a", "R1", 3000, [r1_spec([la])])
    r1_files(e.d("R1a", "dry"), la, {"aud": {"quiet_a": {"n": 20}, "big": {"n": 20, "eff": 0.4}}, "impl": {"q": {"n": 20}}, "feat": {}})
    code, err, so, out = e.run(seed_set="dry")
    T = table(out)
    r = find(T, rule="big", level=1, reading="eff")[0]
    check("dry seed set: same code path, one seed, items from the output (20), unnamed none", code == 0 and r["named_in_seeds"] == ["dry"] and r["items"] == 20 and jo(out, "report_extras.json")["seeds"] == ["dry"], (code, err))
    check("dry seed set: counts against the dry plan's 20 items (no 'other than the plan' entry)", jo(out, "report_extras.json")["rows_with_an_item_count_other_than_the_plan"] == [])
    # wrong class table hash
    bad = os.path.join(ROOT, "badtable.json")
    jdump(bad, json.load(open(CLASS_TABLE)) | {"x": 1})
    e = Env("hash")
    e.surv = {"R1": [la]}
    e.unit("R1a", "R1", 3000, [r1_spec([la])])
    for s in SEEDS:
        quiet_r1(e.d("R1a", s), la)
    code, err, so, out = e.run(class_table=bad)
    check("a class table with another SHA-256 is refused (exit 4)", code == 4 and "SHA-256" in err, (code, err))
    # an output field the field table does not list
    e = Env("unknownfield")
    e.surv = {"R1": [la]}
    e.unit("R1a", "R1", 3000, [r1_spec([la])])
    for s in SEEDS:
        quiet_r1(e.d("R1a", s), la)
    p = e.d("R1a", "1") + f"/{la}.aud.jsonl"
    rows = [json.loads(x) for x in open(p)]
    os.rename(p, p + ".orig")
    wlines(p, [{**r, "surprise": 1} for r in rows])
    code, err, so, out = e.run()
    check("a field that is not in the field table stops, naming the unit and the field", code == 3 and "unit=R1a" in err and "surprise" in err and not os.path.exists(out), (code, err))
    # a field table that lists oracle_any_literal as read would read it: the R-46 fields come from the table
    ft = json.load(open(FIELD_TABLE))
    ft["forms"]["c1_a3"]["scopes"]["level"]["oracle_any_literal"] = {"status": "read", "role": "rule_scalar", "note": "test", "decimals": 3}
    fp = os.path.join(ROOT, "ft_with_oracle.json")
    jdump(fp, ft)
    e = Env("r46table")
    lid = "C1.cond_chain_f3"
    e.surv = {"C1": [lid]}
    e.unit("C1a", "C1", 2000, [{"form": "c1_a3", "run_log": "a3/run_log.json", "must_contain": [lid], "per_survivor": {lid: {"primary_file": "a3/c__own.json", "primary_key": lid, "fallback_file": None, "fallback_key": None, "run_log_key": lid}}}])
    for s in SEEDS:
        d = e.d("C1a", s)
        jdump(d + "/a3/c__own.json", {lid: {str(v): {"n": 2000, "MF_cv": 0.05, "MF_printform_cv": 0.05, "MF_shape_cv": 0.05, "BEST_generic_cv": 0.05, "BEST_generic_chosen": [], "oracle_any_literal": 0.9, "shapes": {}, "S": {}, "distinct_keys": 1} for v in L7}})
        jdump(d + "/a3/run_log.json", {lid: {"alias": "a", "alias_err": "", "alias_rc": 0, "own_err": "", "own_rc": 0}})
    code, err, so, out = e.run(field_table=fp)
    T = table(out)
    check("R-46 comes from the field table: with the field listed as read, oracle_any_literal is read (and drops)", bool(find(T, rule="oracle_any_literal")) and [x["lineage"] for x in jo(out, "dropped.json")] == [lid], code)
    e.name = "r46table_real"
    e.root = e.root + "_real_table"
    for s in SEEDS:
        os.makedirs(e.d("C1a", s) + "/a3", exist_ok=True)
        jdump(e.d("C1a", s) + "/a3/c__own.json", {lid: {str(v): {"n": 2000, "MF_cv": 0.05, "MF_printform_cv": 0.05, "MF_shape_cv": 0.05, "BEST_generic_cv": 0.05, "BEST_generic_chosen": [], "oracle_any_literal": 0.9, "shapes": {}, "S": {}, "distinct_keys": 1} for v in L7}})
        jdump(e.d("C1a", s) + "/a3/run_log.json", {lid: {"alias": "a", "alias_err": "", "alias_rc": 0, "own_err": "", "own_rc": 0}})
    code, err, so, out2 = e.run()
    check("... and with the real field table the same outputs drop nothing (oracle_any_literal is not read)", code == 0 and not find(table(out2), rule="oracle_any_literal") and jo(out2, "dropped.json") == [], (code, err))


def main():
    for t in (t_threshold_and_drop, t_rounding, t_one_seed_and_classes, t_shape_dependent_variants, t_cond, t_nonsurvivor_alias_missing_stop, t_r1_exact_and_amendment_and_feat, t_m1, t_c1_eff_and_classes, t_r1c_stdout, t_misc):
        try:
            t()
        except Exception as ex:  # a test that cannot run is a failure
            import traceback
            global FAIL
            FAIL += 1
            print("FAIL", t.__name__, "raised", repr(ex))
            traceback.print_exc()
    print(f"RESULT pass={PASS} fail={FAIL} run_dir={ROOT}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
