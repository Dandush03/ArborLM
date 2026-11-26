"""Families and builder module files of the written lineages (item 4 and the family count of item 3).

Auditor's script. Imports the four lineage loaders the capacity record's RealSource names
(studies/m0/lineages_r1_fix4_clusters, r2_fix4_set, lineages_m1_fix4, lineages_c1_fix4) to read each
Lineage's `family` and the file that defines its `build` (and the functions its closure wraps).
Generates no item, runs no build function. Writes JSON to --out (and families.json beside it).

Usage (from the implementation worktree root):
  PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python <this> --root . --out <file>
"""

from __future__ import annotations

import argparse
import ast
import functools
import hashlib
import inspect
import json
import subprocess
import sys
from pathlib import Path


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def funcs_behind(fn, seen=None):
    """The function and every function reachable through closures, defaults, partials, __wrapped__ and
    global function names of studies.m0 that its code (or nested code) names."""
    seen = seen if seen is not None else set()
    if id(fn) in seen:
        return []
    seen.add(id(fn))
    out = []
    if isinstance(fn, functools.partial):
        out += funcs_behind(fn.func, seen)
        for v in list(fn.args) + list((fn.keywords or {}).values()):
            if callable(v):
                out += funcs_behind(v, seen)
        return out
    if inspect.isfunction(fn):
        out.append(fn)
        for cell in fn.__closure__ or ():
            try:
                v = cell.cell_contents
            except ValueError:
                continue
            if callable(v):
                out += funcs_behind(v, seen)
            elif isinstance(v, (list, tuple, dict)):
                for w in (v.values() if isinstance(v, dict) else v):
                    if callable(w):
                        out += funcs_behind(w, seen)
        for v in fn.__defaults__ or ():
            if callable(v):
                out += funcs_behind(v, seen)
        w = getattr(fn, "__wrapped__", None)
        if w is not None:
            out += funcs_behind(w, seen)
        g = fn.__globals__
        codes = [fn.__code__]
        while codes:
            co = codes.pop()
            for name in co.co_names:
                v = g.get(name)
                if inspect.isfunction(v) and (v.__module__ or "").startswith("studies.m0"):
                    out += funcs_behind(v, seen)
            codes += [c for c in co.co_consts if inspect.iscode(c)]
    elif callable(fn) and inspect.isfunction(getattr(type(fn), "__call__", None)):
        out += funcs_behind(type(fn).__call__, seen)
    return out


def static_import_closure(root: Path, start: list[Path]) -> list[Path]:
    """Files under studies/ reachable by import statements from the start files (static, AST)."""
    todo = list(start)
    seen: set[Path] = set()
    while todo:
        f = todo.pop()
        if f in seen or not f.is_file():
            continue
        seen.add(f)
        tree = ast.parse(f.read_text())
        for node in ast.walk(tree):
            mods: list[str] = []
            if isinstance(node, ast.ImportFrom):
                if node.level:
                    base = f.parent
                    for _ in range(node.level - 1):
                        base = base.parent
                    if node.module:
                        mods_paths = [base / Path(*node.module.split("."))]
                    else:
                        mods_paths = [base / n.name for n in node.names]
                    for mp in mods_paths:
                        for cand in (mp.with_suffix(".py"), mp / "__init__.py"):
                            if cand.is_file():
                                todo.append(cand)
                    continue
                if node.module and node.module.startswith("studies"):
                    mods = [node.module] + [f"{node.module}.{n.name}" for n in node.names]
            elif isinstance(node, ast.Import):
                mods = [n.name for n in node.names if n.name.startswith("studies")]
            for m in mods:
                relp = Path(*m.split("."))
                for cand in (root / f"{relp}.py", root / relp / "__init__.py"):
                    if cand.is_file():
                        todo.append(cand)
    return sorted(seen)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    root = Path(a.root).resolve()
    sys.path.insert(0, str(root))
    before = set(sys.modules)
    from studies.m0.lineages_c1_fix4 import all_written
    from studies.m0.lineages_m1_fix4 import load_registered
    from studies.m0.lineages_r1_fix4_clusters import candidates_v4, registered_v4
    from studies.m0.r2_fix4_set import fix4_set

    lins = {}
    for ev, got in (
        ("R1", {x.id: x for x in [*candidates_v4(), *registered_v4()]}),
        ("R2", dict(fix4_set())),
        ("M1", {x.id: x for x in load_registered()}),
        ("C1", dict(all_written())),
    ):
        for lid, lin in got.items():
            assert lid not in lins, lid
            assert lin.eval == ev
            lins[lid] = lin
    loaded_files = sorted(
        str(Path(m.__file__).resolve().relative_to(root))
        for n, m in sys.modules.items()
        if n not in before and getattr(m, "__file__", None) and str(Path(m.__file__).resolve()).startswith(str(root))
    )
    reg = json.loads((root / "studies/m0/manifests/registration_record.json").read_text())["registered_lineages"]
    surv = json.loads((root / "studies/m0/manifests/survivor_list_of_record.json").read_text())["evaluations"]
    surv_all = sorted(x for v in surv.values() for x in v)
    missing = [x for x in surv_all if x not in lins]
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()

    def rel(p: str) -> str:
        return str(Path(p).resolve().relative_to(root))

    def inroot(p) -> bool:
        return bool(p) and str(Path(p).resolve()).startswith(str(root))

    per = {}
    for lid in surv_all:
        lin = lins[lid]
        b = lin.build
        fs = funcs_behind(b)
        files = sorted({rel(inspect.getsourcefile(f)) for f in fs if inroot(inspect.getsourcefile(f))})
        top = inspect.getsourcefile(b) if inspect.isfunction(b) else None
        per[lid] = {
            "family": lin.family,
            "build_qualname": getattr(b, "__qualname__", repr(b)),
            "build_module": getattr(b, "__module__", None),
            "build_defined_in": rel(top) if inroot(top) else None,
            "files_of_functions_behind_build": files,
        }

    def files_of(ids):
        defining = sorted({per[x]["build_defined_in"] for x in ids if per[x]["build_defined_in"]})
        behind = sorted({f for x in ids for f in per[x]["files_of_functions_behind_build"]})
        closure = static_import_closure(root, [root / f for f in behind])
        return defining, behind, sorted(str(p.relative_to(root)) for p in closure)

    def hashes(lst):
        return {f: sha(root / f) for f in lst}

    d65, b65, c65 = files_of(reg)
    d82, b82, c82 = files_of(surv_all)
    loaders = [
        "studies/m0/lineages_c1_fix4.py", "studies/m0/lineages_m1_fix4.py",
        "studies/m0/lineages_r1_fix4_clusters.py", "studies/m0/r2_fix4_set.py",
    ]
    res = {
        "what": "Files that define the builders of the registered lineages, with SHA-256 at HEAD of claude/m0-impl. Auditor's listing for G-gen's record (item 4 of the records check). Independent engineering evidence; not Astra validation, not human approval.",
        "head": head,
        "generators_commit_named_in_record": "7cd0ac5a",
        "method": "the four loaders that capacity.py RealSource uses were imported; per lineage, (a) the file that defines Lineage.build, (b) every file of a function reachable from it through closures, partials, defaults, __wrapped__ and global function names of studies.m0 named in its code (runtime introspection), (c) the static import closure (AST) of the files of (b) under studies/; (d) every file of the worktree that the import of the four loaders loaded. No build function was called; no item generated.",
        "registered_65": {
            "n_lineages": len(reg),
            "a_build_defined_in": hashes(d65),
            "b_files_of_functions_behind_build": hashes(b65),
            "c_static_import_closure": hashes(c65),
        },
        "survivors_82": {
            "n_lineages": len(surv_all),
            "missing_from_loaders": missing,
            "a_build_defined_in": hashes(d82),
            "b_files_of_functions_behind_build": hashes(b82),
            "c_static_import_closure": hashes(c82),
        },
        "d_files_loaded_by_importing_the_four_loaders": hashes(loaded_files),
        "loaders": hashes(loaders),
        "per_lineage": per,
    }
    Path(a.out).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    Path(a.out).with_name("families.json").write_text(json.dumps({"family": {x: per[x]["family"] for x in per}}, indent=1, sort_keys=True) + "\n")
    print("registered", len(reg), "a", len(d65), "b", len(b65), "c", len(c65), "| survivors a", len(d82), "b", len(b82), "c", len(c82), "| loaded", len(loaded_files), "| missing", missing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
