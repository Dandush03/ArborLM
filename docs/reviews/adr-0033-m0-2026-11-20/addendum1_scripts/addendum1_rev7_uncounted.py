"""ADR-0033 addendum 1, draft 7: the closed list of uncounted rules, and two standard errors.

Reads committed source files at one commit of branch claude/m0-impl through `git show` (read-only)
and parses them with `ast`. It imports and executes none of them, runs no rule script, generates no
item, reads no run output and computes no lineage figure. Standard library only.

Part A writes the closed list (a JSON table) of the rules that the fresh run of section 4A stage 1S
leaves uncounted, per evaluation, each entry copied as a literal from a committed file whose SHA-256
is recorded. Part B prints the sizes. Part C prints the binomial standard errors for the two item
counts that differ from the stated items per level (check 6, K12 and K15).

Usage, from the root of the worktree that holds branch claude/m0-impl:
  uv run --locked python -I -B <this file> <out table .json>  > <out .txt>
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import re
import subprocess
import sys
from typing import Any

COMMIT = "b78e58b1f47619f070dfc6c0a88999d345b1a34b"
R = "docs/reviews/m0-lineage-decision-2026-11-25"
SOURCES: dict[str, str] = {}


def show(path: str) -> str:
    raw = subprocess.run(["git", "show", f"{COMMIT}:{path}"], check=True, capture_output=True, timeout=60).stdout
    SOURCES[path] = hashlib.sha256(raw).hexdigest()
    return raw.decode("utf-8")


def top_literal(tree: ast.Module, name: str) -> Any:
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id == name:
            return ast.literal_eval(node.value)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name and node.value is not None:
            return ast.literal_eval(node.value)
    raise KeyError(name)


def str_constants(node: ast.AST) -> list[str]:
    return [n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def func(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise KeyError(name)


# ---------------------------------------------------------------- R1
def r1() -> dict[str, Any]:
    ft = ast.parse(show(f"{R}/audit4_r1/final_table4.py"))
    excl, m = top_literal(ft, "EXCL"), top_literal(ft, "M")
    generic, cheap = top_literal(ft, "GENERIC"), top_literal(ft, "CHEAP")
    bat = ast.parse(show("studies/m0/r1_fix3_battery.py"))
    excluded, by_shape = top_literal(bat, "EXCLUDED"), top_literal(bat, "EXCLUDED_BY_SHAPE")
    entries, counted = [], []
    for name in sorted(excl | m):
        label = "EXCL" if name in excl else "M"
        if name in excl and name in m:
            counted.append({"rule": name, "why": "in both EXCL and M of final_table4.py: two readings"})
            continue
        if name in generic or name in cheap:
            counted.append({"rule": name, "why": f"in {label} and in GENERIC or CHEAP of final_table4.py: two readings"})
            continue
        if label == "EXCL":
            if name in excluded:
                scope: Any = "every R1 lineage"
            else:
                scope = sorted(b for b, names in by_shape.items() if name in names)
                if not scope:
                    counted.append({"rule": name, "why": "EXCL in final_table4.py, not excluded by r1_fix3_battery.py: two readings"})
                    continue
            entries.append({"rule": name, "label": "EXCL", "match": "bare name equal", "lineage_stems": scope})
        else:
            entries.append({"rule": name, "label": "M", "match": "bare name equal", "lineage_stems": "every R1 lineage"})
    impl_names = set(excluded) | {x for names in by_shape.values() for x in names}
    return {
        "units": ["R1a", "R1b"],
        "name_rule": "bare name = the rule name with a leading 'a3:' or 'a4:' removed, as bare() of final_table4.py; lineage stem = the id without 'R1.' and without a trailing _r<digits>, as r1_fix3_battery.summarise",
        "entries": entries,
        "considered_and_counted": counted,
        "notes": {
            "EXCL_size": len(excl),
            "M_size": len(m),
            "implementer_exclusions_equal_EXCL_as_names": impl_names == set(excl),
            "M_names_with_a_class_in_r1_fix3_battery": sorted(set(m) & impl_names),
            "every_other_rule": "counted: classes C and A, every 'feat:' row, every rule of new_rules_final.py (R1c), every exact row whose rule is not an entry",
        },
    }


# ---------------------------------------------------------------- R2
R2_LABELS = {"P", "artifact", "partial", "construct", "cue"}


def r2() -> dict[str, Any]:
    fp = ast.parse(show(f"{R}/final_r2/f_pool.py"))
    bt = ast.parse(show("studies/m0/r2_fix4_battery.py"))
    lists = {}
    for nm in ("MISREAD", "PARTIAL", "CONSTRUCT"):
        a, b = top_literal(fp, nm), top_literal(bt, nm)
        assert a == b, nm
        lists[nm] = a
    ka, kb = func(fp, "klass"), func(bt, "klass")
    same_body = [ast.dump(x) for x in ka.body] == [ast.dump(x) for x in kb.body]
    art_any = ["[a3] ignore reverses", "[a3] ignore moves to the end"]
    art_shape = [("[a3] removal by deleting the minimum and keeping the order of the rest", "removals=0")]
    art_l0 = ["[a3] only the first rule", "[a3] only the last rule, on the start string", "[a3] rules in reverse order"]
    p_exact = ["[a3] rules in reverse order", "[mine] [cond] rules in reverse order",
               "[mine] [cond] all rules applied to the start string at once (left to right, first matching rule)"]
    mine = set(art_any) | {x for x, _ in art_shape} | {s for _, s in art_shape} | set(art_l0) | set(p_exact) | {"(P"}
    in_code = set(str_constants(ka)) - R2_LABELS
    assert in_code == mine, sorted(in_code ^ mine)
    entries: list[dict[str, Any]] = [{"order": 1, "match": "name contains", "text": "(P", "label": "P"}]
    entries += [{"order": 2, "match": "name equal", "text": x, "label": "artifact"} for x in art_any]
    entries += [{"order": 3, "match": "name equal, and shape equal", "text": x, "shape": s, "label": "artifact"} for x, s in art_shape]
    entries += [{"order": 4, "match": "name equal, and level 0", "text": x, "label": "artifact"} for x in art_l0]
    entries += [{"order": 5, "match": "name equal", "text": x, "label": "P"} for x in p_exact]
    entries += [{"order": 6, "match": "name starts with", "text": x, "label": "P"} for x in lists["MISREAD"]]
    entries += [{"order": 7, "match": "name contains", "text": x, "label": "partial"} for x in lists["PARTIAL"]]
    fn = ast.parse(show(f"{R}/final_r2/f_new_heur.py"))
    new_entries, new_counted = [], []
    for node in ast.walk(fn):
        if isinstance(node, ast.FunctionDef):
            for d in node.decorator_list:
                if isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "rule":
                    lin, name = (ast.literal_eval(a) for a in d.args)
                    toks = re.findall(r"\((cue|partial|P|artifact)\)", name)
                    row = {"lineage_stem": lin, "rule": "[NEW] " + name, "label": toks[0] if len(toks) == 1 else None}
                    # the header of f_new_heur.py defines three labels: (cue), (partial), (P); a rule with any other label counts
                    (new_entries if len(toks) == 1 and toks[0] in ("partial", "P") else new_counted).append(row)
    return {
        "units": ["R2a", "R2b"],
        "name_rule": "the entries are klass() of final_r2/f_pool.py, in its order; the first entry that matches gives the class; a rule that reaches 'construct' or 'cue' is counted. A rule whose name starts with '[NEW] ' is classed by the entries under new_rules only",
        "entries": entries,
        "new_rules": {"entries": new_entries, "counted": new_counted},
        "considered_and_counted": [{"match": "name contains", "text": x, "label": "construct", "why": "none of the four classes of item 18"} for x in lists["CONSTRUCT"]],
        "notes": {"klass_bodies_identical_in_f_pool_and_r2_fix4_battery": same_body,
                  "klass_source_sha256": hashlib.sha256(ast.unparse(ka).encode()).hexdigest(),
                  "shape_dependent_entries": len(art_shape), "level_dependent_entries": len(art_l0),
                  "new_rules_counted_for_a_label_the_header_of_f_new_heur_does_not_define": [e["rule"] for e in new_counted if e["label"] not in ("cue", "partial", "P")]},
    }


# ---------------------------------------------------------------- M1
def find_rule(tree: ast.Module, name: str) -> tuple[ast.Assign, list[list[ast.stmt]], set[str]] | None:
    """The assignment h["name"] = ..., the statement lists that enclose it (innermost last), and the function's parameters."""
    fn = func(tree, "spec")
    params = {a.arg for a in fn.args.args}

    def walk(stmts: list[ast.stmt], chain: list[list[ast.stmt]]) -> tuple[ast.Assign, list[list[ast.stmt]]] | None:
        for i, st in enumerate(stmts):
            here = chain + [stmts[: i + 1]]
            if isinstance(st, ast.Assign) and isinstance(st.targets[0], ast.Subscript):
                t = st.targets[0]
                if isinstance(t.value, ast.Name) and t.value.id == "h" and isinstance(t.slice, ast.Constant) and t.slice.value == name:
                    return st, here
            for field in ("body", "orelse"):
                sub = getattr(st, field, None)
                if isinstance(sub, list) and sub and isinstance(sub[0], ast.stmt) and not isinstance(st, ast.FunctionDef):
                    got = walk(sub, here)
                    if got:
                        return got
        return None

    got = walk(fn.body, [])
    return (got[0], got[1], params) if got else None


def bound_by(st: ast.stmt) -> set[str]:
    out: set[str] = set()
    if isinstance(st, ast.FunctionDef):
        out.add(st.name)
    elif isinstance(st, ast.Assign | ast.AugAssign | ast.AnnAssign):
        targets = st.targets if isinstance(st, ast.Assign) else [st.target]
        for t in targets:
            out |= {n.id for n in ast.walk(t) if isinstance(n, ast.Name)}
    elif isinstance(st, ast.Import | ast.ImportFrom):
        out |= {(a.asname or a.name).split(".")[0] for a in st.names}
    return out


def definition(tree: ast.Module, name: str) -> tuple[list[str], list[int]] | None:
    """The rule's right-hand side and, recursively, the last statement before it that binds each name it reads."""
    got = find_rule(tree, name)
    if got is None:
        return None
    node, chain, params = got
    prior: list[ast.stmt] = []
    for lst in chain:
        prior += lst[:-1]
    dumps, lines, seen = [ast.dump(node.value)], [node.lineno], set(params) | {"h"}
    todo = [n.id for n in ast.walk(node.value) if isinstance(n, ast.Name)]
    limit = node.lineno
    while todo:
        nm = todo.pop(0)
        if nm in seen:
            continue
        seen.add(nm)
        binders = [st for st in prior if nm in bound_by(st) and st.lineno < limit]
        if not binders:
            dumps.append(f"module-level or builtin name: {nm}")
            continue
        st = binders[-1]
        dumps.append(ast.dump(st))
        lines.append(st.lineno)
        reads = st.body if isinstance(st, ast.FunctionDef) else [st.value] if getattr(st, "value", None) is not None else []
        for part in reads:
            todo += [n.id for n in ast.walk(part) if isinstance(n, ast.Name)]
    return dumps, sorted(set(lines))


def m1() -> dict[str, Any]:
    proc = top_literal(ast.parse(show(f"{R}/audit4_m1/short_summary_a4.py")), "PROC")
    a3 = ast.parse(show(f"{R}/audit3_m1/shortcuts_a3.py"))
    im = ast.parse(show("studies/m0/m1_fix3_shortcuts.py"))
    show(f"{R}/final_m1/pool_a5.py")
    entries, counted = [], []
    for stem in sorted(proc):
        for key in sorted(proc[stem]):
            reason = proc[stem][key]
            if "kept as a rule" in reason:
                counted.append({"lineage_stem": stem, "rule": key, "why": "in PROC, but its reason string in short_summary_a4.py reads 'kept as a rule': a doubt, so it counts"})
                continue
            entries.append({"lineage_stem": stem, "rule": key, "label": "PROC", "match": "prefixed key equal"})
    listed = {(e["lineage_stem"], e["rule"]) for e in entries}
    for stem in sorted(proc):
        for key in sorted(proc[stem]):
            bare = key.split(":", 1)[1]
            da = definition(a3, bare)
            if da is None:
                continue
            row: dict[str, Any] = {"lineage_stem": stem, "rule": "a3:" + bare, "audit3_lines": da[1]}
            if not key.startswith("im:"):
                counted.append({**row, "why": "the PROC rule of the same name is not an implementer rule; no definition to compare"})
                continue
            di = definition(im, bare)
            assert di is not None, bare
            row["implementer_lines"] = di[1]
            if (stem, key) not in listed:
                counted.append({**row, "why": "the PROC rule of the same name is itself counted"})
            elif da[0] == di[0]:
                entries.append({**row, "label": "PROC, by name and definition", "match": "prefixed key equal"})
            else:
                counted.append({**row, "why": "same name; the definition differs between audit3_m1/shortcuts_a3.py and studies/m0/m1_fix3_shortcuts.py at the lines given (right-hand side, or a statement that binds a name it reads)"})
    return {
        "units": ["M1a", "M1b", "M1c"],
        "name_rule": "lineage stem = the id without 'M1.' and without a trailing _r4, _r3 or _r2, as stem() of final_m1/pool_a5.py; in M1a's output the section 'own' gives the prefix 'im:', 'a3' gives 'a3:', and keys of section 'a4' are taken as written",
        "entries": entries,
        "considered_and_counted": counted,
        "notes": {"PROC_pairs": sum(len(v) for v in proc.values()),
                  "definition_test": "an audit-3 rule is an entry only if the implementer rule of the same name is an entry and the two assignments h[name] = ... are equal as parsed (ast.dump), together with, recursively, the last statement before each that binds every name it reads inside spec(); a name bound at module level must be the same name",
                  "every_other_rule": "counted, the 'new:' rules included"},
    }


# ---------------------------------------------------------------- C1
def c1() -> dict[str, Any]:
    f4b_src = show(f"{R}/final_c1/f4b_pool_v2.py")
    f4b = ast.parse(f4b_src)
    bmut, amut = top_literal(f4b, "BATTERY_MUT"), top_literal(f4b, "A3_MUT")
    prefix_map = None
    for node in ast.walk(f4b):
        if isinstance(node, ast.Dict) and all(isinstance(k, ast.Constant) for k in node.keys) and all(isinstance(v, ast.Constant) for v in node.values):
            d = ast.literal_eval(node)
            if set(d) == {"S", "F", "M", "H"}:
                prefix_map = d
    assert prefix_map == {"S": "cheap", "F": "closed", "M": "partial", "H": "hazard"}, prefix_map
    s4 = ast.parse(show(f"{R}/audit4_c1/s4_rules_v2.py"))
    s4_names = sorted({c for c in str_constants(s4) if re.fullmatch(r"[MH]\.[A-Za-z0-9_.]+", c)})
    s4_dynamic = sorted({ast.unparse(n) for n in ast.walk(s4) if isinstance(n, ast.JoinedStr) and n.values and isinstance(n.values[0], ast.Constant)
                         and str(n.values[0].value).startswith(("M.", "H."))})
    s5_src = show(f"{R}/audit4_c1/s5_analyse_v2.py")
    written = '("S", "F", "M", "H")' in s5_src
    eff_f = 'eff(its, ("S", "G", "M", "F"))' in s5_src
    bat = ast.parse(show("studies/m0/c1_fix3_battery.py"))
    controls = sorted({c for c in str_constants(bat) if re.fullmatch(r"C\.[A-Za-z0-9_]+", c)})
    a3 = set(str_constants(ast.parse(show(f"{R}/audit3_c1/a3_shortcuts.py"))))
    assert amut <= a3, sorted(amut - a3)
    f5 = {c for c in str_constants(ast.parse(show(f"{R}/final_c1/f5_closed_forms.py"))) if re.fullmatch(r"[A-Z]\.[A-Za-z0-9_]+", c)}
    f5b = {c for c in str_constants(ast.parse(show(f"{R}/final_c1/f5b_closed_forms_v2.py"))) if re.fullmatch(r"[A-Z]\.[A-Za-z0-9_]+", c)}
    assert f5 == f5b
    entries: list[dict[str, Any]] = [{"source": "a4 (s5_analyse_v2.py output)", "match": "measure equal", "text": "EFF_SM", "label": "partial"}]
    entries += [{"source": "a4 (s5_analyse_v2.py output, field rules)", "match": "rule name equal (after 'shape|')", "text": x,
                 "label": prefix_map[x[0]]} for x in s4_names]
    entries += [{"source": "battery (c1_fix4_battery.py output, field S)", "match": "rule name equal (after 'shape|')", "text": x, "label": "control"} for x in controls]
    entries += [{"source": "a3 (a3_shortcuts.py output, field S)", "match": "rule name equal (after 'shape|')", "text": x, "label": "artefact_a3"} for x in sorted(amut)]
    entries += [{"source": "closed forms (f5_closed_forms.py and f5b_closed_forms_v2.py output)", "match": "rule name equal", "text": x,
                 "label": prefix_map[x[0]]} for x in sorted(f5) if x[0] in ("M", "H")]
    counted = [{"source": "a4", "text": "EFF_F", "why": "no class in f4b_pool_v2.py, which does not read it; counts as written (see notes)"}]
    counted += [{"source": "battery", "text": x, "why": "BATTERY_MUT: partial trace in f4b_pool_v2.py's strict reading, cheap in the implementer's: two readings"} for x in sorted(bmut)]
    counted += [{"source": "closed forms", "text": x, "why": "prefix F or S: closed form or cheap"} for x in sorted(f5) if x[0] not in ("M", "H")]
    return {
        "units": ["C1a", "C1b", "C1c"],
        "name_rule": "an entry applies only to outputs of its source; the same name in another source is counted unless it is an entry there",
        "entries": entries,
        "considered_and_counted": counted,
        "notes": {"prefix_classes_in_f4b_pool_v2": prefix_map,
                  "s4_rules_v2_M_or_H_names_built_at_run_time": s4_dynamic,
                  "s5_analyse_v2_writes_single_rules_only_for_prefixes_S_F_M_H": written,
                  "EFF_F_is_eff_over_S_G_M_F": eff_f,
                  "EFF_F": "its G.* component rules are not written one by one by s5_analyse_v2.py, and the per-shape choice among classes is written nowhere else, so its components cannot all be read separately",
                  "X_rules": "s5_analyse_v2.py writes no X.* rule and f4b_pool_v2.py has no class for one; none is an entry, so one that appeared would count",
                  "every_other_rule": "counted: EFF_S, MF, MFsh, MF_cv, MF_shape_cv, BEST_generic_cv, every S.* and F.* rule, and any rule that is not an entry"},
    }


def main() -> None:
    table = {"commit": COMMIT, "R1": r1(), "R2": r2(), "M1": m1(), "C1": c1()}
    table["source_sha256"] = dict(sorted(SOURCES.items()))
    text = json.dumps(table, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        fh.write(text)
    print("ADR-0033 addendum 1, draft 7: closed list of uncounted rules, from committed code at", COMMIT)
    print("table SHA-256:", hashlib.sha256(text.encode("utf-8")).hexdigest())
    print()
    print("Part A. Source files read (git show), SHA-256")
    for p, h in sorted(SOURCES.items()):
        print(f"  {h}  {p}")
    print()
    print("Part B. Sizes of the closed list")
    a = table["R1"]
    by = {lab: sum(e["label"] == lab for e in a["entries"]) for lab in ("EXCL", "M")}
    print(f"  R1: {len(a['entries'])} bare names (EXCL {by['EXCL']} of {a['notes']['EXCL_size']}, of which limited to named lineage stems: "
          f"{sum(e['label'] == 'EXCL' and e['lineage_stems'] != 'every R1 lineage' for e in a['entries'])}; M {by['M']} of {a['notes']['M_size']}); "
          f"considered and counted: {len(a['considered_and_counted'])}")
    print(f"      implementer's exclusions equal EXCL as a set of names: {a['notes']['implementer_exclusions_equal_EXCL_as_names']}; "
          f"M names with a class in r1_fix3_battery.py: {len(a['notes']['M_names_with_a_class_in_r1_fix3_battery'])}")
    b = table["R2"]
    lab = {x: sum(e["label"] == x for e in b["entries"]) for x in ("P", "artifact", "partial")}
    print(f"  R2: {len(b['entries'])} entries of klass() (P {lab['P']}, artifact {lab['artifact']}, partial {lab['partial']}; shape-dependent "
          f"{b['notes']['shape_dependent_entries']}, level-dependent {b['notes']['level_dependent_entries']}) and {len(b['new_rules']['entries'])} of "
          f"{len(b['new_rules']['entries']) + len(b['new_rules']['counted'])} new rules by name; total {len(b['entries']) + len(b['new_rules']['entries'])}")
    print(f"      klass() bodies identical in f_pool.py and r2_fix4_battery.py: {b['notes']['klass_bodies_identical_in_f_pool_and_r2_fix4_battery']}; "
          f"construct entries counted: {len(b['considered_and_counted'])}")
    c = table["M1"]
    n_a3 = sum(e["rule"].startswith("a3:") for e in c["entries"])
    print(f"  M1: {len(c['entries'])} (lineage stem, key) pairs ({len(c['entries']) - n_a3} of {c['notes']['PROC_pairs']} PROC pairs; {n_a3} audit-3 pairs by name and "
          f"definition); considered and counted: {len(c['considered_and_counted'])}")
    for row in c["considered_and_counted"]:
        print(f"      counted: {row['lineage_stem']} {row['rule']}: {row['why']}"
              + (f" [a3 lines {row['audit3_lines']}" + (f", implementer lines {row['implementer_lines']}]" if "implementer_lines" in row else "]") if "audit3_lines" in row else ""))
    for row in c["entries"]:
        if row["rule"].startswith("a3:"):
            print(f"      entry:   {row['lineage_stem']} {row['rule']} [a3 lines {row['audit3_lines']}, implementer lines {row['implementer_lines']}]")
    d = table["C1"]
    src = {}
    for e in d["entries"]:
        src[e["source"].split(" ")[0]] = src.get(e["source"].split(" ")[0], 0) + 1
    print(f"  C1: {len(d['entries'])} names ({', '.join(f'{k} {v}' for k, v in src.items())}); considered and counted: {len(d['considered_and_counted'])}")
    print(f"      M.* or H.* names built at run time in s4_rules_v2.py: {d['notes']['s4_rules_v2_M_or_H_names_built_at_run_time']}")
    print(f"      s5_analyse_v2.py writes single rules only for prefixes S, F, M, H: {d['notes']['s5_analyse_v2_writes_single_rules_only_for_prefixes_S_F_M_H']}; "
          f"EFF_F is eff over (S, G, M, F): {d['notes']['EFF_F_is_eff_over_S_G_M_F']}")
    print()
    print("Part C. Binomial standard error sqrt(p(1-p)/n) for the two item counts written into the scripts (three seeds)")
    for what, n in (("M1a, digit_puzzle lineages: 300 per level and seed", 900), ("R1a, fitted feature lookups: tested on 1,000 per level and seed", 3000)):
        print(f"  {what}: n = {n}: " + ", ".join(f"p = {p}: {math.sqrt(p * (1 - p) / n):.4f}" for p in (0.15, 0.65, 0.5)))


if __name__ == "__main__":
    main()
