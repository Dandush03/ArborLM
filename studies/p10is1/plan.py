# ruff: noqa: E501
"""P10IS1 plan, freeze identity and registered preconditions (ADR-0024 sections 11, 17.1, 18).

``freeze/plan.json`` is the one source of every stage's items: the cells (labels, lengths, snapshots, rates, seeds), the ladder cells with U0, the granted length G and the projection, the stage caps, the hashes of the draws'
manifests. Every stage derives its items from that file only (``stage_items``); a stage whose items are not all in the plan refuses at the freeze. The frozen-input set is exactly section 18's: ``studies/p10is1/**`` (code,
launch scripts, freeze files other than the plan itself), the config (which holds every threshold and rule parameter), ``freeze/plan.json`` with the granted lengths and the projection, the stage caps, the calibration
record and the data manifests, each by SHA-256; the imported code (``studies/p10s1``, ``studies/p9``, ``studies/p9i``, ``studies/p9ii``, ``src/arborlm``) by comparison with the FREEZE COMMIT (never HEAD), listed file by file;
``uv.lock`` by hash. The ADR text is NOT in it (its hash is provenance only). Registered entry points refuse unless the tree is clean, the freeze commit is an ancestor of HEAD, the frozen files equal their content
at it, the plan exists with every identity in it, the platform is the platform of record, and a committed Decision 2 names the freeze commit.
"""

import ast
import fnmatch
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import canonical_json, file_sha256, read_json, sha256

from . import core, gates

REGISTERED, REHEARSAL, TEST = core.MODES
STAGES = ("gates", "timing", "train", "ladder", "evaluate", "baselines", "analysis", "report", "throughput")
REGISTERED_STAGES = STAGES
FREEZE_RECORD = core.FREEZE_DIR / "freeze_record.json"
FROZEN_ROOTS = ("studies/p10is1",)
IMPORTED_ROOTS = ("studies/p10s1", "studies/p9", "studies/p9i", "studies/p9ii", "src/arborlm")
FROZEN_EXTRA = ("uv.lock",)
DECISION_2_GLOB = "results/p10is1-freeze-*/DECISION_2.md"
DECISION_RUN_LINE = "DECISION: RUN"
DECISION_NO_RUN_LINE = "DECISION: DO NOT RUN"
BASE_PLAN_ABOVE_BUDGET = "BASE PLAN ABOVE BUDGET"
THROUGHPUT_ARMS = ("F-OQ", "T-OQ", "H8", "D-OQ")
StageRefused = core.StageRefused


def git(repo: Path, *argv: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(repo), *argv], capture_output=True, check=False)  # noqa: S603, S607


# --- frozen-input hashes ----------------------------------------------------------------------------------------------------------------------------
def frozen_file_hashes(repo: Path) -> dict[str, str]:
    """SHA-256 of every file of ``studies/p10is1/**`` (sources, launch scripts, freeze files other than ``plan.json`` and the freeze record), of the config and of ``uv.lock``. ``__pycache__`` is not a source."""
    out: dict[str, str] = {}
    skip = {repo / core.PLAN, repo / FREEZE_RECORD}
    for root in FROZEN_ROOTS:
        for p in sorted((repo / root).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc" and p not in skip and "superseded" not in p.parts:
                out[str(p.relative_to(repo))] = file_sha256(p)
    out[str(core.CONFIG)] = file_sha256(repo / core.CONFIG)
    for extra in FROZEN_EXTRA:
        if (repo / extra).is_file():
            out[extra] = file_sha256(repo / extra)
    return out


def adr_provenance(repo: Path) -> dict[str, str]:
    return {"path": core.SPEC, "sha256": file_sha256(repo / core.SPEC), "note": "provenance only: the ADR text is not a frozen input and no check compares this hash"}


def imported_modules(repo: Path) -> list[str]:
    """The transitive closure of a static import walk from ``studies/p10is1`` into the imported roots, file by file (repository-relative paths)."""
    seen: set[Path] = set()
    todo = [p for p in (repo / "studies/p10is1").rglob("*.py") if "__pycache__" not in p.parts]
    out: set[str] = set()

    def module_files(mod: str) -> list[Path]:
        rel = Path(*mod.split("."))
        found = []
        for base in (repo / "src", repo):
            for cand in (base / rel.with_suffix(".py"), base / rel / "__init__.py"):
                if cand.is_file():
                    found.append(cand)
        return found

    while todo:
        f = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module, *(f"{node.module}.{a.name}" for a in node.names)]
            for n in names:
                for p in module_files(n):
                    rel = str(p.relative_to(repo))
                    if rel.startswith(tuple(IMPORTED_ROOTS)):
                        out.add(rel)
                        todo.append(p)
                    elif rel.startswith("studies/p10is1"):
                        todo.append(p)
    return sorted(out)


def imported_vs_commit(repo: Path, commit: str, files: Sequence[str]) -> list[str]:
    """Each imported file in the working tree must equal the same path at the freeze commit (HEAD is never compared: a later commit that touches none of these paths stops nothing). Returns the files that differ."""
    bad = []
    for f in files:
        at = git(repo, "rev-parse", f"{commit}:{f}")
        now = git(repo, "hash-object", f)
        if at.returncode != 0 or at.stdout.strip() != now.stdout.strip():
            bad.append(f)
    return bad


# --- items from the plan only -----------------------------------------------------------------------------------------------------------------------
def stage_items(plan: "Plan", stage: str) -> list[dict[str, Any]]:
    """The items of a stage, derived from the plan file only (the lesson of P10-S1's throughput stage, which listed a cell the frozen plan did not run)."""
    cells = plan.data["cells"]
    if stage == "train":
        return [{"id": core.item_id("train", c["label"]), "cell": c["label"], "to": int(c["u0"]) if c["ladder_cell"] else int(c["run"])} for c in cells]
    if stage == "ladder":
        names = []
        for c in cells:
            n = core.cell_name(c["facts"], c["slots"])
            if c["ladder_cell"] and n not in names:
                names.append(n)
        return [{"id": core.item_id("ladder", n), "cell_name": n, "labels": [c["label"] for c in cells if c["ladder_cell"] and core.cell_name(c["facts"], c["slots"]) == n], "u0": int(next(c for c in cells if c["ladder_cell"] and core.cell_name(c["facts"], c["slots"]) == n)["u0"]), "granted": int(plan.data["params"]["granted"][n])} for n in names]
    if stage == "evaluate":
        return [{"id": core.item_id("evaluate", c["label"]), "cell": c["label"], "updates": list(c["snapshots"])} for c in cells if not c["ladder_cell"]]
    if stage == "baselines":
        seen: list[tuple[int, int]] = []
        for c in cells:
            k = (c["draw"], c["facts"])
            if k not in seen:
                seen.append(k)
        return [{"id": f"baselines|d{d}|f{f}", "draw": d, "facts": f, "cell": next(c["label"] for c in cells if (c["draw"], c["facts"]) == (d, f))} for d, f in seen]
    if stage == "timing":
        keys: list[tuple[str, int]] = []
        for c in cells:
            if (c["arm"], c["slots"]) not in keys:
                keys.append((c["arm"], c["slots"]))
        return [{"id": f"timing|{a}|{n}", "arm": a, "slots": n} for a, n in keys]
    if stage == "throughput":
        out, seen2 = [], set()
        first = min(c["draw"] for c in cells)
        for c in cells:
            if c["draw"] != first or c["arm"] not in THROUGHPUT_ARMS:
                continue
            for arm in ((c["arm"], "F-OQ-IVF") if c["arm"] == "F-OQ" and c["slots"] != 256 else (c["arm"],)):
                key = (arm, c["facts"], c["slots"])
                if key in seen2:
                    continue
                seen2.add(key)
                out.append({"id": f"throughput|{arm}|{c['facts']}|{c['slots']}", "arm": arm, "facts": c["facts"], "slots": c["slots"], "cell": c["label"], "update": int(c["u_p"])})
        return out
    if stage in ("gates", "analysis", "report"):
        return [{"id": stage}]
    raise ValueError(f"unknown stage {stage!r}")


# --- the plan --------------------------------------------------------------------------------------------------------------------------------------
class Plan:
    """The plan file, read only. ``stage_items`` and everything else come from the file."""

    def __init__(self, data: Mapping[str, Any], path: Path | None = None) -> None:
        if data.get("kind") != "freeze_plan" or data.get("study") != core.STUDY or data.get("schema") != core.SCHEMA:
            raise StageRefused("refused: not a P10IS1 plan")
        self.data, self.path = dict(data), path

    @classmethod
    def load(cls, path: Path) -> "Plan":
        if not path.is_file():
            raise StageRefused(f"refused: no freeze plan at {path}: nothing registered runs before the freeze")
        return cls(read_json(path), path)

    @property
    def mode(self) -> str:
        return str(self.data["mode"])

    def params(self) -> core.PlanParams:
        return core.PlanParams.from_json(self.data["params"])

    def items(self, stage: str) -> list[dict[str, Any]]:
        return stage_items(self, stage)

    def cell(self, label: str) -> dict[str, Any]:
        for c in self.data["cells"]:
            if c["label"] == label:
                return dict(c)
        raise StageRefused(f"refused: {label} is not a cell of the frozen plan")

    def cap_seconds(self, name: str) -> float:
        return float(self.data["stage_caps"][f"{name}_hours"]) * 3600.0

    def sha256(self) -> str:
        return sha256(canonical_json(self.data))


def build_plan(*, mode: str, cfg: Mapping[str, Any], repo: Path, params: core.PlanParams, run_dir: Path, projection: Mapping[str, Any] | None = None, extra: Mapping[str, Any] | None = None, draws: Sequence[int] = range(1, 6)) -> dict[str, Any]:
    """The plan record (a pure function of its inputs). Identity of every frozen file, the config, the caps, the cells; the projection of section 17.1 with the granted lengths. A base plan above the budget is written as such
    and the freeze refuses it."""
    if mode not in core.MODES:
        raise ValueError(f"unknown mode {mode!r}")
    cells = core.planned_cells(params, mode, cfg, draws=draws)
    proj = dict(projection) if projection is not None else None
    rec: dict[str, Any] = {
        **core.envelope("freeze_plan"), "mode": mode, "adr": adr_provenance(repo), "config_sha256": core.config_sha256(repo / core.CONFIG), "frozen_files": frozen_file_hashes(repo), "imported_files": imported_modules(repo),
        "stage_caps": {k: float(v) for k, v in cfg["caps"].items() if k.endswith("_hours")}, "caps_provisional": bool(cfg["caps"]["provisional"]), "run_dir": str(run_dir.resolve()), "params": params.to_json(), "cells": cells,
        "projection": proj, "base_plan_above_budget": bool(proj and proj.get("refused")), "platform": gates.platform_record(), "lane_l": core.LANE_L_NOT_LICENSED, "not_tested_x": core.NOT_TESTED_X,
        "frozen_input_set": "studies/p10is1/** (code, launch scripts, freeze files), the config, freeze/plan.json (granted lengths and projection), stage caps, calibration record, data manifests, uv.lock by SHA-256; imported code of studies/p10s1, studies/p9*, src/arborlm by comparison with the freeze commit; the ADR text is not in it",
    }  # fmt: skip
    rec.update(dict(extra or {}))
    return rec


def verify_plan(plan: Plan, repo: Path, run_dir: Path, *, candidate: bool = False, freeze_commit: str | None = None) -> None:
    """Every identity the plan recorded must hold now: the frozen files and the config (SHA-256), the caps (equal to the config's and not provisional), the data manifests, the run directory, the imported files against the
    freeze commit, and (registered) the freeze record. A difference is PAUSED — IDENTITY: restoring the file bit for bit resumes the stage."""
    d = plan.data
    now = frozen_file_hashes(repo)
    differ = sorted(k for k in set(now) | set(d["frozen_files"]) if now.get(k) != d["frozen_files"].get(k))
    if differ:
        raise StageRefused("refused: frozen file(s) differ from the freeze (PAUSED — IDENTITY): " + ", ".join(differ[:8]))
    cfg = core.load_config(repo / core.CONFIG)
    caps = {k: float(v) for k, v in cfg["caps"].items() if k.endswith("_hours")}
    if caps != d["stage_caps"]:
        raise StageRefused("refused: the stage caps in the config differ from the plan's")
    if d["mode"] == REGISTERED and not candidate and (core.caps_provisional(cfg) or d.get("caps_provisional")):
        raise StageRefused("refused: the caps are provisional: the caps are set after the measuring rehearsal and the plan is rewritten and rehearsed again (section 11)")
    if d.get("base_plan_above_budget") and not candidate:
        raise StageRefused(f"refused: {BASE_PLAN_ABOVE_BUDGET}: the freeze refuses this plan and the work returns to the human lead (section 17.1 item 2)")
    if Path(d["run_dir"]).resolve() != run_dir.resolve():
        raise StageRefused(f"refused: the freeze names the run directory {d['run_dir']}, not {run_dir}")
    for name, rec in (d.get("manifests") or {}).items():
        p = Path(rec["path"]) if Path(rec["path"]).is_absolute() else repo / rec["path"]
        if not p.is_file() or file_sha256(p) != rec["sha256"]:
            raise StageRefused(f"refused: {p} does not hash to the frozen manifest {name}")
    if d["mode"] == REGISTERED and not candidate:
        verify_freeze_record(plan, repo)
        if freeze_commit:
            bad = imported_vs_commit(repo, freeze_commit, d["imported_files"])
            if bad:
                raise StageRefused("refused: imported file(s) differ from the freeze commit (PAUSED — IDENTITY): " + ", ".join(bad[:8]))
        if d["imported_files"] != imported_modules(repo):
            raise StageRefused("refused: the imported set differs from the freeze's static import walk (PAUSED — IDENTITY)")


# --- registered preconditions ---------------------------------------------------------------------------------------------------------------------------
def check_preconditions(mode: str, repo: Path, freeze_commit: str | None) -> dict[str, str] | None:
    """A registered stage refuses unless the working tree is clean, ``freeze_commit`` is an ancestor of HEAD, ``studies/p10is1`` and the config equal their content at that commit, the imported roots equal theirs, and the
    machine is the platform of record. Returns the freeze identity (None for rehearsal and test)."""
    if mode != REGISTERED:
        return None
    dirty = git(repo, "status", "--porcelain", "--untracked-files=all").stdout.decode().strip()
    if dirty:
        raise StageRefused("refused: the working tree is not clean:\n" + "\n".join(dirty.splitlines()[:10]))
    if not freeze_commit:
        raise StageRefused("refused: a registered stage requires --freeze-commit")
    ok = git(repo, "rev-parse", "--verify", "--quiet", f"{freeze_commit}^{{commit}}")
    if ok.returncode != 0:
        raise StageRefused(f"refused: {freeze_commit} is not a commit of this repository")
    full = ok.stdout.decode().strip()
    if git(repo, "merge-base", "--is-ancestor", full, "HEAD").returncode != 0:
        raise StageRefused(f"refused: freeze commit {full} is not an ancestor of HEAD")
    problems = [f"{p} at HEAD differs from the freeze commit" for p in (*FROZEN_ROOTS, *IMPORTED_ROOTS, str(core.CONFIG), *FROZEN_EXTRA) if git(repo, "rev-parse", f"{full}:{p}").stdout != git(repo, "rev-parse", f"HEAD:{p}").stdout]
    if problems:
        raise StageRefused("refused: " + "; ".join(problems))
    bad = gates.platform_problems()
    if bad:
        raise StageRefused("refused: not the platform of record (section 16): " + "; ".join(bad))
    return {"commit": full, "tree": git(repo, "rev-parse", f"{full}^{{tree}}").stdout.decode().strip()}


def require_ignored_run_dir(repo: Path, run_dir: Path) -> None:
    """A run directory inside the repository must be git-ignored: otherwise the first record makes the tree dirty and every later worker refuses."""
    try:
        rel = run_dir.resolve().relative_to(repo.resolve())
    except ValueError:
        return
    if git(repo, "check-ignore", "-q", str(rel) + "/x").returncode != 0:
        raise StageRefused(f"refused: the run directory {run_dir} is inside the repository and is not git-ignored")


def require_ignored_path(repo: Path, path: Path) -> None:
    """A file this study writes inside the repository (the ledger) must be git-ignored: writing it would dirty the tree."""
    try:
        rel = path.resolve().relative_to(repo.resolve())
    except ValueError:
        return
    if git(repo, "check-ignore", "-q", str(rel)).returncode != 0:
        raise StageRefused(f"refused: {path} is inside the repository and is not git-ignored: writing it would dirty the tree")


def require_decision_2(repo: Path, freeze_commit: str) -> str:
    """Decision 2 is recorded in a committed file ``results/p10is1-freeze-*/DECISION_2.md`` that holds the line ``DECISION: RUN`` (and not ``DECISION: DO NOT RUN``) and the full freeze commit. Without it no registered
    stage starts."""
    full = git(repo, "rev-parse", "--verify", "--quiet", f"{freeze_commit}^{{commit}}").stdout.decode().strip()
    tracked = [p for p in git(repo, "ls-tree", "-r", "--name-only", "HEAD", "--", "results").stdout.decode().split("\n") if fnmatch.fnmatch(p, DECISION_2_GLOB)]
    for name in tracked:
        text = git(repo, "show", f"HEAD:{name}").stdout.decode("utf-8", "replace")
        lines = {line.strip() for line in text.splitlines()}
        if full and full in text and DECISION_RUN_LINE in lines and DECISION_NO_RUN_LINE not in lines:
            return name
    raise StageRefused(f"refused: no committed {DECISION_2_GLOB} contains the line '{DECISION_RUN_LINE}' (and not '{DECISION_NO_RUN_LINE}') and the full freeze commit {full or freeze_commit}: Decision 2 is recorded there before anything registered runs")


def verify_freeze_record(plan: Plan, repo: Path) -> dict[str, Any]:
    """The freeze record (``freeze/freeze_record.json``, hashed with the other frozen files) names the SHA-256 of the committed ``plan.json`` and of the rehearsal record whose candidate section rehearsed that very file."""
    path = repo / FREEZE_RECORD
    if not path.is_file():
        raise StageRefused(f"refused: no freeze record at {path}")
    rec = read_json(path)
    if rec.get("kind") != "freeze_record" or rec.get("plan_file_sha256") != file_sha256(repo / core.PLAN):
        raise StageRefused("refused: the freeze record does not name the SHA-256 of the committed plan.json")
    return dict(rec)


def load_registered_plan(repo: Path) -> Plan:
    plan = Plan.load(repo / core.PLAN)
    if plan.mode != REGISTERED:
        raise StageRefused("refused: the plan in freeze/ is not a registered plan")
    return plan
