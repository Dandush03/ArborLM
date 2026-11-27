"""Step 2: transitive dependency closure of the 20 listed scripts at b78e58b1, by parsing source (AST) read
with `git cat-file`; nothing in the repository is executed or imported.

Static edges: every `import` / `from ... import` anywhere in a file (module level or inside functions),
resolved against an ordered search path that is fixed per entry point (ENTRY_PATH below; each list is
taken from reading the entry's own sys.path handling and its documented run command; see REPORT.md).
`studies.*` and `arborlm.*` resolve to the tree; a package import also counts its __init__.py files.
Dynamic edges (importlib / subprocess / open of a needed file) cannot be resolved by AST alone; they are
listed in MANUAL with file:line, from reading, and the resolver checks each target exists at the commit.
Every other call that can reach a file (open, Path, exec, subprocess, importlib, sys.path edits) found in
any file of the closure is printed in `call_sites` so that a reader can see none was left unexamined."""
import ast, hashlib, json, subprocess, sys

REPO = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
COMMIT = "b78e58b1"
D = "docs/reviews/m0-lineage-decision-2026-11-25/"
ROOT = ""

def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], check=True, capture_output=True).stdout

TREE = {}
for line in git("ls-tree", "-r", "-z", COMMIT).split(b"\0"):
    if line:
        meta, path = line.split(b"\t", 1)
        TREE[path.decode()] = meta.split()[2].decode()

def text(p):
    return git("cat-file", "blob", TREE[p]).decode()

def sha(p):
    return hashlib.sha256(git("cat-file", "blob", TREE[p])).hexdigest()

def dirof(p):
    return p.rsplit("/", 1)[0] if "/" in p else ""

def j(d, name):
    return f"{d}/{name}" if d else name

# ordered sys.path (directories, "" = worktree root) in force when the entry's imports run
ENTRY_PATH = {
    "studies/m0/r1_fix4_measure.py": [ROOT],
    "studies/m0/r2_fix4_battery.py": [ROOT],
    "studies/m0/m1_fix4_battery.py": [D + "audit3_m1", D + "audit4_m1", ROOT],
    "studies/m0/c1_fix4_battery.py": [ROOT],
    "studies/m0/c1_fix4_draw.py": [ROOT],
    "studies/m0/c1_fix4_a3_run.py": [ROOT],
    D + "final_r1/run_rules_final.py": [ROOT, D + "final_r1", D + "final_r1/a4copy"],
    D + "final_r1/new_rules_final.py": [ROOT, D + "final_r1"],
    D + "final_r2/f_rules.py": [D + "audit3_r2", D + "audit4_r2", D + "final_r2", ROOT],
    D + "final_r2/f_rules_new.py": [D + "final_r2", ROOT],
    D + "final_r2/f_new_heur.py": [D + "final_r2"],
    D + "final_m1/rules_a5.py": [D + "audit3_m1", D + "audit4_m1", D + "final_m1", ROOT],
    D + "final_m1/rules_a5_attempt1.py": [D + "audit3_m1", D + "audit4_m1", D + "final_m1", ROOT],
    D + "final_c1/f1_draw.py": [ROOT, D + "final_c1"],
    D + "final_c1/f3_a3_run.py": [D + "final_c1"],
    D + "final_c1/f5_closed_forms.py": [D + "final_c1"],
    D + "final_c1/f5b_closed_forms_v2.py": [D + "final_c1"],
    D + "audit4_c1/s4_rules_v2.py": [D + "audit4_c1"],
    D + "audit4_c1/s5_analyse_v2.py": [D + "audit4_c1"],
    D + "audit3_c1/a3_shortcuts.py": [D + "audit3_c1"],
}

# dynamic edges, from reading (file:line of the call; target as the code computes it at the run root)
MANUAL = [
    ("studies/m0/m1_fix4_battery.py", 87, D + "audit4_m1/common_a4.py", "importlib path (spec_from_file_location; ROOT = Path(__file__).resolve().parents[2], line 33)"),
    ("studies/m0/m1_fix4_battery.py", 90, D + "audit4_m1/shortcuts_a4.py", "importlib path (spec_from_file_location; ROOT = Path(__file__).resolve().parents[2], line 33)"),
    ("studies/m0/m1_fix4_battery.py", 94, D + "audit3_m1/common_a3.py", "importlib path (spec_from_file_location; ROOT = Path(__file__).resolve().parents[2], line 33)"),
    ("studies/m0/m1_fix4_battery.py", 96, D + "audit3_m1/shortcuts_a3.py", "importlib path (spec_from_file_location; ROOT = Path(__file__).resolve().parents[2], line 33)"),
    (D + "final_m1/rules_a5.py", 50, D + "audit4_m1/shortcuts_a4.py", "importlib path (spec_from_file_location; AUD = Path('docs/reviews/...').resolve(), cwd-relative, line 37)"),
    (D + "final_m1/rules_a5.py", 51, D + "audit3_m1/shortcuts_a3.py", "importlib path (spec_from_file_location; AUD cwd-relative, line 37)"),
    (D + "final_m1/rules_a5_attempt1.py", 48, D + "audit4_m1/shortcuts_a4.py", "importlib path (spec_from_file_location; AUD cwd-relative, line 35)"),
    (D + "final_m1/rules_a5_attempt1.py", 49, D + "audit3_m1/shortcuts_a3.py", "importlib path (spec_from_file_location; AUD cwd-relative, line 35)"),
    (D + "final_m1/fm1_common.py", 17, "studies/m0/manifests/m1_fix4_survivors.json", "file open (json.load(open('studies/m0/manifests/m1_fix4_survivors.json')), cwd-relative, in survivors())"),
    ("studies/m0/c1_fix4_a3_run.py", 60, D + "audit3_c1/a3_shortcuts.py", "subprocess ([sys.executable, '-I', <--a3 path>, dir, out]; path given on the command line)"),
    (D + "final_c1/f3_a3_run.py", 34, D + "audit3_c1/a3_shortcuts.py", "subprocess ([sys.executable, '-I', <argv[2]>, dir, out]; path given on the command line)"),
]

def imports(p):
    t = ast.parse(text(p), filename=p)
    out = []
    for n in ast.walk(t):
        if isinstance(n, ast.Import):
            for a in n.names:
                out.append((n.lineno, a.name, None))
        elif isinstance(n, ast.ImportFrom):
            if n.level:
                out.append((n.lineno, "." * n.level + (n.module or ""), [a.name for a in n.names]))
            else:
                out.append((n.lineno, n.module, [a.name for a in n.names]))
    return sorted(out)

def find_mod(dotted, path):
    """Return (list of repo files executed by importing `dotted`, dir it was found in) or None."""
    parts = dotted.split(".")
    for d in path:
        files = []
        cur = d
        ok = True
        for i, part in enumerate(parts):
            pkg = j(cur, part + "/__init__.py")
            mod = j(cur, part + ".py")
            if pkg in TREE:
                files.append(pkg)
                cur = j(cur, part)
            elif mod in TREE and i == len(parts) - 1:
                files.append(mod)
            else:
                ok = False
                break
        if ok and files:
            return files, d
    return None

def all_hits(name, path):
    return [d for d in path if find_mod(name, [d])]

CALLS = {"open", "Path", "exec", "eval", "compile", "__import__", "run", "Popen", "check_output", "check_call",
         "call", "system", "import_module", "spec_from_file_location", "run_path", "run_module", "read_text",
         "read_bytes", "write_text", "insert", "load", "exec_module", "getoutput", "glob", "listdir", "chdir"}

def call_sites(p):
    s = text(p)
    t = ast.parse(s, filename=p)
    out = []
    for n in ast.walk(t):
        if isinstance(n, ast.Call):
            f = n.func
            nm = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "?")
            if nm in CALLS:
                seg = ast.get_source_segment(s, n) or ""
                if nm in ("insert",) and "sys.path" not in seg:
                    continue
                if nm == "run" and "subprocess" not in seg:
                    continue
                if nm == "load" and "json" not in seg and "pickle" not in seg:
                    continue
                out.append([n.lineno, nm, seg[:200]])
    return sorted(out)

def main():
    stdlib = set(sys.stdlib_module_names)
    listed = list(ENTRY_PATH)
    deps = {}         # path -> {entry: set(how)}
    externals = {}    # top-level name -> set of importing files
    ambiguous = []
    unresolved = []
    for entry in listed:
        path = ENTRY_PATH[entry]
        seen = set()
        todo = [entry]
        for (src, line, tgt, how) in MANUAL:
            pass
        while todo:
            f = todo.pop()
            if f in seen:
                continue
            seen.add(f)
            if not f.endswith(".py"):
                continue
            fpath = [dirof(f)] + [d for d in path if d != dirof(f)] if not f.startswith("studies/") else path
            for (line, mod, names) in imports(f):
                if mod.startswith("."):
                    unresolved.append([entry, f, line, mod, "relative import"])
                    continue
                top = mod.split(".")[0]
                r = find_mod(mod, fpath)
                if r is None:
                    if top in stdlib or top in ("torch",):
                        continue
                    if find_mod(top, fpath) is None:
                        externals.setdefault(top, set()).add(f)
                        continue
                    unresolved.append([entry, f, line, mod, "package found, module not"])
                    continue
                files, d = r
                hits = all_hits(mod, fpath)
                if len(hits) > 1:
                    ambiguous.append([entry, f, line, mod, hits])
                # from pkg import name  -> name may be a submodule
                extra = []
                if names:
                    for nm in names:
                        sub = find_mod(mod + "." + nm, [d])
                        if sub:
                            extra += [x for x in sub[0] if x not in files]
                for x in files + extra:
                    kind = "import" if x == files[-1] or x in extra else "import (package __init__)"
                    if x != entry:
                        deps.setdefault(x, {}).setdefault(entry, set()).add(f"{kind}: {f}:{line} `{mod}`" + (f" {names}" if names else ""))
                    todo.append(x)
            for (src, line, tgt, how) in MANUAL:
                if src == f:
                    if tgt not in TREE:
                        unresolved.append([entry, f, line, tgt, "MANUAL target missing at commit"])
                        continue
                    deps.setdefault(tgt, {}).setdefault(entry, set()).add(f"{how}: {f}:{line}")
                    todo.append(tgt)
    listed_set = set(listed)
    out_deps = []
    for p in sorted(deps):
        if p in listed_set:
            continue
        out_deps.append({"path": p, "blob": TREE[p], "sha256": sha(p),
                         "reached_by": sorted(deps[p]),
                         "how": sorted({h for e in deps[p] for h in deps[p][e]})})
    listed_reached = {p: {e: sorted(v) for e, v in deps[p].items()} for p in sorted(deps) if p in listed_set}
    closure = sorted(set(listed) | {d["path"] for d in out_deps})
    sites = {p: call_sites(p) for p in closure if p.endswith(".py")}
    json.dump({"commit": git("rev-parse", COMMIT).decode().strip(), "dependencies": out_deps,
               "listed_scripts_reached_from_other_listed": listed_reached,
               "external_top_level_imports": {k: sorted(v) for k, v in sorted(externals.items())},
               "ambiguous_bare_names": ambiguous, "unresolved": unresolved, "call_sites": sites,
               "entry_path": ENTRY_PATH, "manual_edges": MANUAL},
              sys.stdout, sort_keys=True, indent=2)
    sys.stdout.write("\n")

main()
