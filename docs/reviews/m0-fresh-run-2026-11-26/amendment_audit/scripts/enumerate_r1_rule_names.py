"""Amendment audit (M0 fresh run, ADR-0033 addendum 1): enumerate, by PARSING ONLY, the rule names that units R1a, R1b, R1c can
write for the ten R1 survivor lineages, at commit b78e58b1. Reads files through `git show`; imports and executes none of them.
Standard library only. Usage (from the implementation worktree):
  uv run --locked python <this> <out.json>
"""
import ast
import json
import subprocess
import sys

COMMIT = "b78e58b1f47619f070dfc6c0a88999d345b1a34b"
D = "docs/reviews/m0-lineage-decision-2026-11-25/"
FILES = {
    "a3_studies": "studies/m0/r1_fix4_a3_heur.py",
    "a4_studies": "studies/m0/r1_fix4_a4_heur.py",
    "impl": "studies/m0/r1_fix3_battery.py",
    "tells": "studies/m0/r1_fix4_tells.py",
    "a3_copy": D + "final_r1/a4copy/heuristics3.py",
    "a4_copy": D + "final_r1/a4copy/heuristics4.py",
    "r1b": D + "final_r1/run_rules_final.py",
    "r1c": D + "final_r1/new_rules_final.py",
    "table4": D + "audit4_r1/final_table4.py",
}
# base name -> functions that write rule names for it (from the dispatch tables SPECIFIC / NEW / _OLD / EXTRA / SPEC, read by hand)
A3FN = {"boolean_lights": "h_boolean", "categories_default_exceptions": "h_cde", "compass_turns": "h_compass", "conditional_threshold_rule": "h_threshold",
        "equivalence_exchange_rates": "h_exchange", "knights_knaves": "h_kk", "spatial_grid_walk": "h_grid", "swap_tracking": "h_swap",
        "temporal_weekday_shift": "h_weekday", "venn_counting": "h_venn"}
A4FN = {"equivalence_exchange_rates": "n_exch", "knights_knaves": "n_kk", "swap_tracking": "n_swap", "temporal_weekday_shift": "n_weekday"}  # _r5/_r6 ids only
IMPL_EXTRA = {"equivalence_exchange_rates": "h_exch5"}
R1C = {"knights_knaves": [], "temporal_weekday_shift": ["wk_rules"], "categories_default_exceptions": ["cde_rules"], "compass_turns": ["compass_rules"]}
SURV = ["R1.boolean_lights_r4", "R1.categories_default_exceptions_r4", "R1.compass_turns", "R1.conditional_threshold_rule_r4",
        "R1.equivalence_exchange_rates_r6", "R1.knights_knaves_r6", "R1.spatial_grid_walk_r5", "R1.swap_tracking_r5",
        "R1.temporal_weekday_shift_r6", "R1.venn_counting_r5"]


def src(k):
    return subprocess.run(["git", "show", f"{COMMIT}:{FILES[k]}"], capture_output=True, text=True, check=True).stdout


def fn_keys(tree, name):
    """String keys of dict literals and of `<var>["..."] = ...` assignments inside function `name`."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            keys = set()
            for sub in ast.walk(node):
                if isinstance(sub, ast.Dict):
                    for k in sub.keys:
                        if isinstance(k, ast.Constant) and isinstance(k.value, str):
                            keys.add(k.value)
                if isinstance(sub, ast.Assign):
                    for t in sub.targets:
                        if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) and isinstance(t.slice.value, str):
                            keys.add(t.slice.value)
            return keys
    raise KeyError(name)


def generic_keys(tree):
    """generic(): keys per answer-type branch, read from the If tests by hand: first If = name/text, second = number."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "generic":
            ifs = [s for s in node.body if isinstance(s, ast.If)]
            out = []
            for i in ifs:
                ks = set()
                for sub in ast.walk(i):
                    if isinstance(sub, ast.Assign):
                        for t in sub.targets:
                            if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant):
                                ks.add(t.slice.value)
                out.append(sorted(ks))
            return {"name_text": out[0], "number": out[1]}


def set_literal(tree, var):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == var for t in node.targets):
            return sorted(ast.literal_eval(node.value))
    raise KeyError(var)


def dict_keys_of_assign(tree, var):
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == var for t in node.targets) and isinstance(node.value, ast.Dict):
            return node
    raise KeyError(var)


def main():
    T = {k: ast.parse(src(k)) for k in FILES}
    M = set_literal(T["table4"], "M")
    EXCL = set_literal(T["table4"], "EXCL")
    ANSWER_TYPE = {"R1.boolean_lights_r4": "yn", "R1.categories_default_exceptions_r4": "yn", "R1.compass_turns": "word",
                   "R1.conditional_threshold_rule_r4": "yn", "R1.equivalence_exchange_rates_r6": "number", "R1.knights_knaves_r6": "word",
                   "R1.spatial_grid_walk_r5": "name", "R1.swap_tracking_r5": "text", "R1.temporal_weekday_shift_r6": "word",
                   "R1.venn_counting_r5": "number"}  # read from each builder's Built(...) by hand
    SIZE_BASES = {"equivalence_exchange_rates", "venn_counting"}  # SIZE of r1_fix4_a4_heur.py restricted to the ten; k is None for both
    out = {"commit": COMMIT, "M": M, "EXCL": EXCL, "lineages": {}}
    for lid in SURV:
        base = lid.split(".", 1)[1]
        for suf in ("_r4", "_r5", "_r6"):
            base = base.removesuffix(suf)
        at = ANSWER_TYPE[lid]
        rec = {}
        for unit, a3k, a4k in (("R1a", "a3_studies", "a4_studies"), ("R1b", "a3_copy", "a4_copy")):
            g = generic_keys(T[a3k])
            gen = g["name_text"] if at in ("name", "text") else g["number"] if at == "number" else []
            aud = set(gen) | {"constant_mfk_fitted"}
            if base in SIZE_BASES:
                aud.add("fitted_ratio_times_size")
            aud |= {"a3:" + k for k in fn_keys(T[a3k], A3FN[base])}
            if lid.endswith(("_r5", "_r6")) and base in A4FN:
                aud |= {"a4:" + k for k in fn_keys(T[a4k], A4FN[base])}
            gi = generic_keys(T["impl"])
            geni = gi["name_text"] if at in ("name", "text") else gi["number"] if at == "number" else []
            impl = set(geni) | {"constant_mfk_fitted"} | fn_keys(T["impl"], A3FN[base])
            if base in IMPL_EXTRA:
                impl |= fn_keys(T["impl"], IMPL_EXTRA[base])
            rec[unit] = {"aud": sorted(aud), "impl": sorted(impl)}
        # fitted lookups (feat:)
        f1 = dict_keys_of_assign(T["tells"], "FEATS_1"); f2 = dict_keys_of_assign(T["tells"], "FEATS_2")
        feats = []
        for d in (f1, f2):
            for k, v in zip(d.keys, d.values):
                if k.value == base:
                    feats += ["feat:" + kk.value for kk in v.keys]
        rec["R1a"]["feat"] = sorted(feats)
        fb = dict_keys_of_assign(T["r1b"], "FEATS")
        featb = []
        for k, v in zip(fb.keys, fb.values):
            if k.value == lid:
                featb += ["feat:" + kk.value for kk in v.keys]
        rec["R1b"]["feat"] = sorted(featb)
        # R1c
        spec = dict_keys_of_assign(T["r1c"], "SPEC")
        r1c = []
        for k, v in zip(spec.keys, spec.values):
            if k.value == lid:
                for kk, vv in zip(v.keys, v.values):
                    if kk.value == "rules":
                        r1c += sorted(fn_keys(T["r1c"], vv.id))
                    elif kk.value == "lookup":
                        r1c += ["lookup " + x.value for x in vv.keys]
        rec["R1c"] = {"printed": sorted(r1c)}
        out["lineages"][lid] = rec
    # bare names and the amendment scope
    def bare(h):
        return h.split(":", 1)[1] if h.startswith(("a3:", "a4:")) else h
    scope = {}
    for lid, rec in out["lineages"].items():
        names = set()
        for u, d in rec.items():
            for lst in d.values():
                names |= set(lst)
        scope[lid] = {"in_amendment_scope": sorted(n for n in names if bare(n) not in M and bare(n) not in EXCL),
                      "labelled_M": sorted(n for n in names if bare(n) in M), "labelled_EXCL": sorted(n for n in names if bare(n) in EXCL)}
    out["scope"] = scope
    with open(sys.argv[1], "w") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    for lid, s in scope.items():
        print(lid, len(s["in_amendment_scope"]), "in scope;", len(s["labelled_M"]), "M;", len(s["labelled_EXCL"]), "EXCL")


main()
