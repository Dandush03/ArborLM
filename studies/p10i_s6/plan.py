# ruff: noqa: E501
"""P10IS6 plan, freeze identity and registered preconditions (ADR-0031 sections 15, 16, 17; the design of ``studies/p10ir`` and ``studies/p10i_s3``).

``freeze/plan.json`` is the one source of every stage's items and carries: the rate table, ``k_max``, the worker count and memory guards, the caps (registered cap = charged so far + 2 x projected remaining from R2, computed by code), the SHA-256 of every
frozen input, the import-walk list of ``src/arborlm`` files, the imported files of P10-I-S3, the run-time ``results/`` inputs, the data manifest hash and the backbone digests. Every stage derives its items from the plan file only. The ADR text is
recorded for provenance and no check compares it.

CODE IDENTITY (requirement 6). Two lists: ``COMPUTING`` (files whose identity binds results: training, evaluation, calibration, corpus, parents, analysis inputs and rules) are hashed into every stage record; ``ORCHESTRATION`` (stage driver, runner, planning, cost,
rehearsal, launch scripts) and ``studies/p10i_s6/printing/`` only print or orchestrate. All files under ``studies/p10i_s6`` except ``printing/`` are frozen inputs checked by workers (section 15); a stage record carries the computing hashes only, so a
later fix to a printed line (``printing/``) voids nothing.

Registered entry points refuse unless the tree is clean, the plan and freeze record exist, the freeze commit is an ancestor of HEAD and equals HEAD on the frozen files, every identity holds, and a committed Decision 2 names the freeze commit.
"""

import ast
import fnmatch
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from arborlm.io import canonical_json, file_sha256, read_json, sha256

from . import core, gates, items

REGISTERED, REHEARSAL, TEST = "registered", "rehearsal", "test"
MODES = (REGISTERED, REHEARSAL, TEST)
REGISTERED_STAGES = ("gates", "train", "eval", "analysis", "report")
FROZEN_ROOTS = ("studies/p10i_s6",)
PRINTING = "studies/p10i_s6/printing"
COMPUTING = ("core", "labels", "analysis", "calibration", "model", "items", "corpus", "parents", "gates", "synthetic", "fetch")
ORCHESTRATION = ("plan", "runner", "stages", "cost", "rehearsal", "testing", "report_input")
DECISION_RUN_LINE, DECISION_NO_RUN_LINE = "DECISION: RUN", "DECISION: DO NOT RUN"
IMPORTED_S3 = ("studies/p10i_s3/model.py", "studies/p10i_s3/calibration.py", "studies/p10i_s3/core.py", "studies/p10i_s3/planted.py", "studies/p10i_s3/data.py", "studies/p10i_s3/parents.py")
RUNTIME_RESULTS_GLOBS = ("results/p3-lt-2026-11-12/b*-control/manifest.json", "results/p3-lt-2026-11-12/b*-control/order.json", "results/p4-2026-11-12/b*-baseline/result.json")
NAMED_SRC = (
    "pilot_model", "model", "pilot_config", "pilot_data", "fetch_wikitext", "io", "p4_model", "p4_config", "p2_model", "engine", "longer_training", "pilot_metrics", "__init__", "config", "data",
    "optimization_followup", "p2_config", "p3_config", "records", "watchdog",
    "checkpoint", "diagnose_memory", "p2_checkpoint", "p2_data", "p3_checkpoint", "p3_data", "p3_parent", "p4_checkpoint", "p4_data", "p4_parent", "pilot_checkpoint",
)  # fmt: skip


class StageRefused(RuntimeError):
    """A registered entry point refuses to run."""


def git(repo: Path, *argv: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(repo), *argv], capture_output=True, check=False)  # noqa: S603, S607


def _imports_of(path: Path, inside_src: bool) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                if inside_src and node.level == 1:
                    if node.module:
                        out.add(node.module)
                    else:
                        out.update(a.name for a in node.names)
            elif node.module and node.module.split(".")[0] == "arborlm":
                rest = node.module.split(".", 1)[1] if "." in node.module else ""
                if rest:
                    out.add(rest)
                else:
                    out.update(a.name for a in node.names)
        elif isinstance(node, ast.Import):
            out.update(a.name.split(".", 1)[1] for a in node.names if a.name.startswith("arborlm."))
    return out


def import_walk(repo: Path) -> list[str]:
    """Every ``src/arborlm`` file reached by a static walk of module-level and function-local imports from every module of ``studies/p10i_s6`` and of the imported P10-I-S3 files."""
    src = repo / "src" / "arborlm"
    todo: set[str] = set()
    starts = sorted((repo / "studies/p10i_s6").rglob("*.py")) + [repo / f for f in IMPORTED_S3 if (repo / f).is_file()]
    for p in starts:
        todo |= {m.split(".")[0] for m in _imports_of(p, False)}
    seen: set[str] = set()
    while todo:
        name = todo.pop()
        if name in seen or not (src / f"{name}.py").is_file():
            continue
        seen.add(name)
        todo |= {m.split(".")[0] for m in _imports_of(src / f"{name}.py", True)}
    return sorted(f"src/arborlm/{n}.py" for n in seen)


def src_identity(repo: Path) -> dict[str, Any]:
    named = [f"src/arborlm/{n}.py" for n in NAMED_SRC]
    walked = import_walk(repo)
    every = sorted(set(named) | set(walked))
    return {"files": {f: file_sha256(repo / f) for f in every if (repo / f).is_file()}, "missing_named": [f for f in named if not (repo / f).is_file()], "named_not_reached": sorted(set(named) - set(walked)), "reached_not_named": sorted(set(walked) - set(named))}


def frozen_file_hashes(repo: Path) -> dict[str, str]:
    """SHA-256 of every file under ``studies/p10i_s6`` except ``printing/``, the plan, the freeze record and ``superseded/``; the config; the tests of this study; ``uv.lock``; ``pyproject.toml``; the imported P10-I-S3 files; the run-time ``results/`` inputs."""
    out: dict[str, str] = {}
    skip = {repo / core.PLAN, repo / core.FREEZE_RECORD}
    for root in FROZEN_ROOTS:
        for p in sorted((repo / root).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc" and p not in skip and "superseded" not in p.parts and "printing" not in p.relative_to(repo / root).parts:
                out[str(p.relative_to(repo))] = file_sha256(p)
    for p in sorted((repo / "tests").glob("test_p10i_s6_*.py")):
        out[str(p.relative_to(repo))] = file_sha256(p)
    for f in (str(core.CONFIG), "uv.lock", "pyproject.toml", *IMPORTED_S3):
        out[f] = file_sha256(repo / f)
    for g in RUNTIME_RESULTS_GLOBS:
        for p in sorted(repo.glob(g)):
            out[str(p.relative_to(repo))] = file_sha256(p)
    return out


def computing_hashes(repo: Path) -> dict[str, str]:
    """The hashes a stage record carries (requirement 6): the computing files only."""
    return {f"studies/p10i_s6/{n}.py": file_sha256(repo / "studies/p10i_s6" / f"{n}.py") for n in COMPUTING} | {str(core.CONFIG): file_sha256(repo / core.CONFIG)}


def adr_provenance(repo: Path) -> dict[str, str]:
    return {"path": core.SPEC, "sha256": file_sha256(repo / core.SPEC), "note": "provenance only: the ADR text is not a frozen input and no check compares this hash"}


class Plan:
    def __init__(self, data: Mapping[str, Any], path: Path | None = None) -> None:
        if data.get("kind") != "freeze_plan" or data.get("study") != core.STUDY or data.get("schema") != core.SCHEMA:
            raise StageRefused("refused: not a P10IS6 plan")
        self.data, self.path = dict(data), path

    @classmethod
    def load(cls, path: Path) -> "Plan":
        if not path.is_file():
            raise StageRefused(f"refused: no freeze plan at {path}: nothing registered runs before the freeze")
        return cls(read_json(path), path)

    def items(self, kind: str) -> list[dict[str, Any]]:
        if kind not in ("train", "eval"):
            raise ValueError(kind)
        return list(self.data["items"][kind])

    def item(self, item_id: str) -> dict[str, Any]:
        for kind in ("train", "eval"):
            for it in self.data["items"][kind]:
                if it["id"] == item_id:
                    return dict(it)
        raise StageRefused(f"refused: {item_id} is not an item of the frozen plan")

    @property
    def mode(self) -> str:
        return str(self.data["mode"])

    @property
    def k_max(self) -> int:
        return int(self.data["k_max"])

    @property
    def rate_table(self) -> dict[str, Any]:
        return dict(self.data["rate_table"])

    def cap_seconds(self) -> float:
        return float(self.data["caps"]["rehearsal_hours" if self.mode != REGISTERED else "registered_hours"]) * 3600.0

    def sha256(self) -> str:
        return sha256(canonical_json(self.data))


def caps_from_projection(charged_hours: float, projected_remaining_hours: float) -> float:
    """THE one formula (requirement 1): the registered cap = charged so far + 2 x projected remaining. The freeze, the caps command and the candidate plan all call this function."""
    return charged_hours + 2.0 * projected_remaining_hours


def build_plan(*, mode: str, cfg: Mapping[str, Any], repo: Path, run_dir: Path, rate_table: Mapping[str, Any], k_max: int, projected_remaining_hours: float | None = None, charged_hours: float = 0.0, extra: Mapping[str, Any] | None = None, plan_items: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}")
    cap = float(cfg["caps"]["registered_hours_bound"])
    provisional = True
    if projected_remaining_hours is not None:
        cap = caps_from_projection(charged_hours, projected_remaining_hours)
        provisional = False
    guard, workers, rss_worker = int(cfg["resources"]["rss_aggregate_bytes"]), int(cfg["resources"]["workers"]), int(cfg["resources"]["rss_worker_bytes"])
    if workers * rss_worker > guard:
        raise ValueError("workers x per-worker guard exceeds the aggregate guard")
    rec: dict[str, Any] = {
        **core.envelope("freeze_plan"), "mode": mode, "adr": adr_provenance(repo), "config_sha256": core.config_sha256(repo / core.CONFIG), "frozen_files": frozen_file_hashes(repo), "computing_files": computing_hashes(repo), "src": src_identity(repo),
        "imports_from_p10i_s3": list(IMPORTED_S3), "k_max": k_max, "rate_table": dict(rate_table), "workers": workers, "rss_worker_bytes": rss_worker, "rss_aggregate_bytes": guard,
        "rss_measure": "process RSS including file-backed pages (G22)", "caps": {"rehearsal_hours": float(cfg["caps"]["rehearsal_hours"]), "registered_hours": cap, "bound_hours": float(cfg["caps"]["registered_hours_bound"]), "rule": "charged so far + 2 x projected remaining from R2's record"},
        "caps_provisional": provisional, "run_dir": str(run_dir.resolve()), "items": dict(plan_items) if plan_items is not None else (items.registered_items(cfg, rate_table, k_max) if mode == REGISTERED else {"train": [], "eval": []}), "platform": gates.platform_record(),
        "seed_plan": {k: sorted(v) for k, v in gates.planned_seed_values(cfg).items()},
        "frozen_input_set": "studies/p10i_s6/** except printing/ (code, freeze files), the config, tests/test_p10i_s6_*.py, the imported P10-I-S3 files, the run-time results/ inputs, the import-walk src/arborlm files, uv.lock, pyproject.toml, the data manifest, the chunk table and the parent checkpoints; the ADR text is not in it",
    }  # fmt: skip
    rec.update(dict(extra or {}))
    return rec


NOT_COMPARED = ("adr", "platform")


def scientific_content(plan_data: Mapping[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in plan_data.items() if k not in NOT_COMPARED}


def verify_identity(plan: Plan, repo: Path) -> None:
    """Every identity the plan recorded must hold now (PAUSED — IDENTITY on a difference): frozen files, config, src files, data manifest files, parent files."""
    d = plan.data
    now = frozen_file_hashes(repo)
    differ = sorted(k for k in set(now) | set(d["frozen_files"]) if now.get(k) != d["frozen_files"].get(k))
    if differ:
        raise StageRefused("refused: frozen file(s) differ from the freeze (PAUSED — IDENTITY): " + ", ".join(differ[:8]))
    src = src_identity(repo)
    if src["files"] != d["src"]["files"]:
        bad = sorted(k for k in set(src["files"]) | set(d["src"]["files"]) if src["files"].get(k) != d["src"]["files"].get(k))
        raise StageRefused("refused: src/arborlm file(s) differ from the freeze (PAUSED — IDENTITY): " + ", ".join(bad[:8]))
    if src["missing_named"]:
        raise StageRefused("refused: a named src file does not exist: " + ", ".join(src["missing_named"]))
    manifest = d.get("data_manifest")
    if manifest:
        p = Path(manifest["path"])
        if not p.is_file() or file_sha256(p) != manifest["sha256"]:
            raise StageRefused(f"refused: {p} does not hash to the frozen data manifest (PAUSED — IDENTITY)")
        for name, digest in read_json(p)["files"].items():
            f = p.parent / name
            if not f.is_file() or file_sha256(f) != digest:
                raise StageRefused(f"refused: {f} does not hash to the data manifest (PAUSED — IDENTITY)")
    for name, digest in (d.get("parent_files") or {}).items():
        f = Path(name)
        if not f.is_file() or file_sha256(f) != digest:
            raise StageRefused(f"refused: parent file {f} does not hash to the plan (PAUSED — IDENTITY)")


def verify_plan(plan: Plan, repo: Path, run_dir: Path, *, candidate: bool = False) -> None:
    verify_identity(plan, repo)
    d = plan.data
    cfg = core.load_config(repo / core.CONFIG)
    if d["mode"] == REGISTERED and not candidate and (d.get("caps_provisional") or bool(cfg["caps"]["provisional"])):
        raise StageRefused("refused: the caps are provisional: the registered cap is set by the rule from R2 and the plan is rewritten and rehearsed again")
    if Path(d["run_dir"]).resolve() != run_dir.resolve():
        raise StageRefused(f"refused: the freeze names the run directory {d['run_dir']}, not {run_dir}")
    if d["mode"] == REGISTERED:
        if d["items"] != items.registered_items(cfg, d["rate_table"], int(d["k_max"])):
            raise StageRefused("refused: the plan's items differ from a re-derivation from the config and the rate table")
        if not candidate:
            verify_freeze_record(plan, repo)


def check_preconditions(mode: str, repo: Path, freeze_commit: str | None) -> dict[str, str] | None:
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
    problems = [f"{p} at HEAD differs from the freeze commit" for p in (*FROZEN_ROOTS, str(core.CONFIG), "src/arborlm", "uv.lock", "pyproject.toml") if git(repo, "rev-parse", f"{full}:{p}").stdout != git(repo, "rev-parse", f"HEAD:{p}").stdout]
    if problems:
        raise StageRefused("refused: " + "; ".join(problems))
    bad = gates.platform_problems(core.load_config(repo / core.CONFIG))
    if bad:
        raise StageRefused("refused: not the platform of record: " + "; ".join(bad))
    return {"commit": full, "tree": git(repo, "rev-parse", f"{full}^{{tree}}").stdout.decode().strip()}


def require_ignored_path(repo: Path, path: Path) -> None:
    """Nothing is written where it dirties the tree: a path inside the repository must be git-ignored."""
    try:
        rel = path.resolve().relative_to(repo.resolve())
    except ValueError:
        return
    if git(repo, "check-ignore", "-q", str(rel) + ("/x" if path.is_dir() or not path.suffix else "")).returncode != 0:
        raise StageRefused(f"refused: {path} is inside the repository and is not git-ignored: writing it would dirty the tree")


def require_decision_2(repo: Path, freeze_commit: str) -> str:
    """A committed ``results/p10i-s6-freeze-*/DECISION_2.md`` with the line ``DECISION: RUN`` (and not ``DECISION: DO NOT RUN``) and the full freeze commit."""
    full = git(repo, "rev-parse", "--verify", "--quiet", f"{freeze_commit}^{{commit}}").stdout.decode().strip()
    tracked = [p for p in git(repo, "ls-tree", "-r", "--name-only", "HEAD", "--", "results").stdout.decode().split("\n") if fnmatch.fnmatch(p, core.DECISION_2_GLOB)]
    for name in tracked:
        text = git(repo, "show", f"HEAD:{name}").stdout.decode("utf-8", "replace")
        lines = {x.strip() for x in text.splitlines()}
        if full and full in text and DECISION_RUN_LINE in lines and DECISION_NO_RUN_LINE not in lines:
            return name
    raise StageRefused(f"refused: no committed {core.DECISION_2_GLOB} contains the line '{DECISION_RUN_LINE}' and the full freeze commit {full or freeze_commit}: Decision 2 is the human lead's own and is recorded there before anything registered runs")


def verify_freeze_record(plan: Plan, repo: Path) -> dict[str, Any]:
    path = repo / core.FREEZE_RECORD
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


RULE_CONFIG_SECTIONS = ("setting", "ladder", "convergence", "rates", "thresholds", "controls", "data", "seeds")
RULE_FILES = ("studies/p10i_s6/labels.py", "studies/p10i_s6/analysis.py", "studies/p10i_s6/calibration.py")


def rule_hashes(repo: Path) -> dict[str, Any]:
    """The hash of the config's rule-bearing sections and of the files that turn measurements into labels and rates. R1 records them; the freeze refuses a difference (no condition is changed after any rehearsal output exists)."""
    cfg = core.load_config(repo / core.CONFIG)
    return {"config_sections": sha256(canonical_json({k: cfg[k] for k in RULE_CONFIG_SECTIONS})), "files": {f: file_sha256(repo / f) for f in RULE_FILES}}
