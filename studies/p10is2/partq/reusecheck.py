# ruff: noqa: E501
"""The freeze-time checks of a plan that REUSES completed stages (ADR-0025 addendum, attempt 3, section 4 conditions 1, 2 and 4).

``confined_diff`` compares, file by file, the frozen set of the code that produced the reused stages (the freeze commit of the earlier attempt) with the working tree, and REFUSES unless every difference is confined to the
template's segment rule, the outputs and analysis stages, the cap check, the reuse mechanism itself, tests and documentation. Enforcement is by code at three levels:

* a file outside the earlier freeze's frozen set (tests, docs, README, the Part T code) is not looked at; a file that is NEW is fine (it cannot have been executed by the reused stages);
* a Python file is compared definition by definition (top-level functions, classes and assignments, by the dump of their syntax tree, so that comments and formatting do not count): a changed or removed definition is
  allowed only if it is in ``ALLOWED_DEFINITIONS`` for that path (or the whole file is in ``ALLOWED_FILES``); added imports and added definitions are allowed; a changed or removed import, or any other module-level
  statement that changed, is refused;
* the config is compared as parsed TOML: only ``stage_caps``, ``caps.provisional`` and (with the ledger check of ``check_ledger_pin``) ``paths.panel_ledger`` may differ; the launch scripts of Part Q may differ only
  where listed; every other frozen file (``common/``, ``uv.lock``, ``pyproject.toml``, the other launch scripts) must be byte-identical.

What code cannot decide, ``MIXED`` names: functions that ARE executed by the reused stages and were edited for the cap check, the stage order, the reuse stage or the analysis (``real_stages.run_stage`` and the
like). The check allows them by name and the freeze record LISTS them (``requires_auditor_certification``): that the edit inside them touches only the allowed behaviour is for the independent auditor to certify from the diff."""

import ast
import tomllib
from pathlib import Path
from typing import Any

from ..common import core
from ..common import plan as planmod
from ..common.core import StageRefused

Q = "studies/p10is2/partq/"
ALLOWED_FILES = {  # whole files: the segment rule, the freeze/plan/rehearsal commands (never executed by the reused stages) and the reuse mechanism
    Q + "gloss.py": "the template's segment rule",
    Q + "freeze.py": "the freeze, plan and caps commands (not executed by a stage)",
    Q + "counting.py": "the rehearsal orchestrators (not executed by a stage)",
    Q + "reuse.py": "the reuse mechanism (new)",
    Q + "reusecheck.py": "this check (new)",
    Q + "promptcheck.py": "the pre-freeze prompt check (new)",
    Q + "plan.py": "the plan builder (a plan is built at the freeze, never by a stage)",
}
ALLOWED_DEFINITIONS: dict[str, set[str]] = {
    Q + "step8.py": {"step_gloss"},  # the gloss test takes the bank that is stored
    Q + "pipeline.py": {"hashes_of"},  # a linked (reused) directory is not an output of the new run
    Q + "pkgmanifest.py": {"verify_inputs"},  # the reuse block's byte check at stage start
    Q + "real_stages.py": {"stage_outputs", "write_manifest", "require_prerequisites", "run_stage", "order_of", "make_ctx", "build_world"},
    Q + "stages.py": {"build_parser", "cmd_registered", "refuse_unless_rehearsal_ready", "main", "REGISTERED_STAGES", "cmd_rehearse", "cmd_ledger"},
    Q + "real.py": {"run_rehearsal", "run_rehearsal_stage", "run_registered_stage"},
}
MIXED = {  # executed by the reused stages and edited: allowed by name, listed in the freeze record for the auditor's certification
    Q + "real_stages.py": {"run_stage", "require_prerequisites", "make_ctx", "build_world", "write_manifest"},
    Q + "pkgmanifest.py": {"verify_inputs"},
    Q + "stages.py": {"build_parser", "cmd_registered", "main", "REGISTERED_STAGES"},
    Q + "pipeline.py": {"hashes_of"},
}
ALLOWED_SCRIPTS = {"studies/p10is2/launch/partq_registered.sh", "studies/p10is2/launch/partq_rehearse.sh", "studies/p10is2/launch/partq_prompt_check.sh"}  # the reuse stage's line; the prompt check (new)
CONFIG_FREE_SECTIONS = {("stage_caps",), ("caps", "provisional"), ("paths", "panel_ledger")}


def _show(repo: Path, commit: str, rel: str) -> str | None:
    r = core.git(repo, "show", f"{commit}:{rel}")
    return r.stdout.decode("utf-8") if r.returncode == 0 else None


def definitions(source: str) -> tuple[dict[str, str], dict[tuple[str, str | None, int], frozenset[tuple[str, str | None]]], list[str]]:
    """(definition name -> dump of its syntax tree, imports as {(kind, module, level): the names imported}, other module-level statements as dumps) of a Python module; the docstring is ignored."""
    tree = ast.parse(source)
    defs: dict[str, str] = {}
    imports: dict[tuple[str, str | None, int], frozenset[tuple[str, str | None]]] = {}
    other: list[str] = []
    for i, node in enumerate(tree.body):
        if isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant) and i == 0:
            continue
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            defs[node.name] = ast.dump(node)
        elif isinstance(node, ast.Assign) and all(isinstance(t, ast.Name) for t in node.targets):
            defs[node.targets[0].id] = ast.dump(node)  # type: ignore[attr-defined]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            defs[node.target.id] = ast.dump(node)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            key = ("from", node.module, node.level) if isinstance(node, ast.ImportFrom) else ("import", None, 0)
            imports[key] = imports.get(key, frozenset()) | frozenset((a.name, a.asname) for a in node.names)
        else:
            other.append(ast.dump(node))
    return defs, imports, other


def python_diff(path: str, old: str, new: str) -> tuple[list[str], list[str]]:
    """(refusals, changed definition names) for one Python file."""
    if path in ALLOWED_FILES:
        return [], ["<whole file>"] if old != new else []
    od, oi, oo = definitions(old)
    nd, ni, no = definitions(new)
    refusals: list[str] = []
    changed = sorted(n for n in set(od) | set(nd) if n in od and (n not in nd or od[n] != nd[n]))  # a new definition (not in od) is an addition
    allowed = ALLOWED_DEFINITIONS.get(path, set())
    refusals += [f"{path}: definition {n!r} changed or was removed and is not an allowed change" for n in changed if n not in allowed]
    removed_imports = [k for k, names in oi.items() if not names <= ni.get(k, frozenset())]  # a name added to an import is an addition; a name or a whole import removed is not
    if removed_imports:
        refusals.append(f"{path}: {len(removed_imports)} import statement(s) changed or removed")
    if oo != no:
        refusals.append(f"{path}: module-level statements other than definitions and imports changed")
    return refusals, changed


def config_diff(old: str, new: str) -> list[str]:
    """Refusals for the config: anything parsed that differs outside ``CONFIG_FREE_SECTIONS``."""
    o, n = tomllib.loads(old), tomllib.loads(new)
    out: list[str] = []

    def walk(a: Any, b: Any, path: tuple[str, ...]) -> None:
        if any(path[: len(f)] == f for f in CONFIG_FREE_SECTIONS):
            return
        if isinstance(a, dict) and isinstance(b, dict):
            for k in sorted(set(a) | set(b)):
                if k not in a or k not in b:
                    out.append(f"config: {'.'.join((*path, k))} was {'added' if k not in a else 'removed'}")
                else:
                    walk(a[k], b[k], (*path, k))
        elif a != b:
            out.append(f"config: {'.'.join(path)} changed from {a!r} to {b!r}")

    walk(o, n, ())
    return out


def confined_diff(repo: Path, old_commit: str, part: str = "Q") -> dict[str, Any]:
    """The file-by-file difference between the frozen set at ``old_commit`` and the working tree, REFUSED unless confined (see the module docstring). Returns the record that goes into the freeze record."""
    listing = core.git(repo, "ls-tree", "-r", "--name-only", old_commit)
    if listing.returncode != 0:
        raise StageRefused(f"refused: {old_commit} is not a commit of this repository")
    now = planmod.frozen_file_hashes(repo, part)
    old_names = {n for n in listing.stdout.decode().splitlines() if n in now or any(n.startswith(r) for r in planmod.PART_ROOTS[part]) or n == str(planmod.part_config(part)) or n in planmod.ALWAYS or n.startswith("studies/p10is2/launch/partq_")}
    refusals: list[str] = []
    record: dict[str, Any] = {"compared_with": old_commit, "identical": 0, "new_files": [], "changed": {}, "requires_auditor_certification": []}
    for rel in sorted(old_names | set(now)):
        if rel.endswith(".pyc") or "__pycache__" in rel:
            continue
        old = _show(repo, old_commit, rel)
        cur = (repo / rel).read_text(encoding="utf-8") if (repo / rel).is_file() and rel in now else None
        if old is None:
            record["new_files"].append(rel)  # not in the earlier freeze: cannot have been executed by the reused stages
            continue
        if cur is None:
            refusals.append(f"{rel}: present at {old_commit}, missing now")
            continue
        if old == cur:
            record["identical"] += 1
            continue
        if rel.endswith(".py"):
            bad, changed = python_diff(rel, old, cur)
            refusals += bad
            record["changed"][rel] = changed
            record["requires_auditor_certification"] += [f"{rel}::{n}" for n in changed if n in MIXED.get(rel, set())]
        elif rel == str(planmod.part_config(part)):
            bad = config_diff(old, cur)
            refusals += bad
            record["changed"][rel] = ["stage_caps / caps.provisional / paths.panel_ledger only" if not bad else "see refusals"]
        elif rel in ALLOWED_SCRIPTS:
            record["changed"][rel] = ["launch script (the reuse stage's branch / the prompt check)"]
            record["requires_auditor_certification"].append(rel)
        else:
            refusals.append(f"{rel}: differs from {old_commit} and is not an allowed change (the reused stages executed it, or it holds the environment)")
    if refusals:
        raise StageRefused(f"refused: the code differs from freeze {old_commit} outside the confined set (segment rule, outputs and analysis stages, cap check, reuse mechanism): " + "; ".join(refusals[:12]) + (f" ... (+{len(refusals) - 12})" if len(refusals) > 12 else ""))
    return record


def check_ledger_pin(repo: Path, old_commit: str, plan: planmod.Plan) -> dict[str, Any]:
    """The reused stages ran against the shared ledger with the hash the earlier plan pinned. The new plan must pin a file with EXACTLY that hash (the preserved copy), so that identity holds and no stage reads the live,
    since-extended ledger."""
    text = _show(repo, old_commit, str(core.PLAN_Q))
    if text is None:
        raise StageRefused(f"refused: no plan at {old_commit}:{core.PLAN_Q}")
    import json

    old = json.loads(text)
    want = (old.get("manifests") or {}).get("panel_ledger", {}).get("sha256")
    have = (plan.data.get("manifests") or {}).get("panel_ledger", {}).get("sha256")
    if not want or want != have:
        raise StageRefused(f"refused: the plan pins a shared ledger of hash {have}, the reused stages ran against {want}: pin the preserved copy by that hash (paths.panel_ledger)")
    return {"pinned_ledger_sha256": have, "path": plan.data["manifests"]["panel_ledger"]["path"], "same_as_earlier_plan": True}


def check_seeds(repo: Path, old_commit: str, plan: planmod.Plan) -> dict[str, Any]:
    """Condition 4: the registered seeds are the same, none replaced."""
    import json

    text = _show(repo, old_commit, str(core.PLAN_Q))
    old = json.loads(text or "{}")
    if old.get("seeds") != plan.data.get("seeds"):
        raise StageRefused("refused: the plan's registered seeds differ from those of the earlier freeze")
    return {"seeds_equal": True, "seeds": plan.data["seeds"]}
