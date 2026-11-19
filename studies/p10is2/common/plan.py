# ruff: noqa: E501
"""Plans, frozen-input identity, the import walk and the registered preconditions (ADR-0025 sections 10, 11 item 2, 19 ruling L1, L11).

Each part has its own candidate plan (``freeze/partq_plan.json``, ``freeze/partt_plan.json``), written first; every stage derives its blocks, cells and items from that file only. The frozen-input sets are
those of section 11 item 2: Part Q ``studies/p10is2/partq/**`` and ``studies/p10is2/common/**``, its config, ``uv.lock``, ``pyproject.toml``, the requirements file and the Part Q launch scripts; Part T
``studies/p10is2/**`` outside ``partq/`` and the freeze directory, its config, ``uv.lock``, ``pyproject.toml``. Every file the import walk reaches outside ``studies/p10is2/`` joins the part's set by file and hash
(including files a reached module READS AT IMPORT: importing ``studies/p10s2`` loads ``configs/p10s2_transfer.toml``, correction C8). The ADR text is NOT a frozen input: the plan stores its hash for
provenance only and nothing compares it.

Registered entry points refuse unless the tree is clean, the freeze commit is an ancestor of HEAD, the part's frozen files equal their content at that commit, the plan and freeze record exist and agree, and a
COMMITTED Decision 2 for the part names the freeze commit. A hash difference found when a task starts is PAUSED — IDENTITY, never a failure.
"""

import fnmatch
import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import canonical_json, file_sha256, read_json, sha256

from . import core, gates
from .core import StageRefused

REGISTERED, REHEARSAL, TEST = core.MODES
IDENTITY_EXIT = 75  # EX_TEMPFAIL: PAUSED — IDENTITY, not FAILED
DECISION_RUN_LINE = "DECISION: RUN"
DECISION_NO_RUN_LINE = "DECISION: DO NOT RUN"
DECISION_2_GLOB = {"Q": "results/p10is2-partq-freeze-*/DECISION_2_PARTQ.md", "T": "results/p10is2-partt-freeze-*/DECISION_2_PARTT.md"}
STUDY_ROOT = "studies/p10is2"
PART_ROOTS = {"Q": ("studies/p10is2/partq", "studies/p10is2/common"), "T": ("studies/p10is2",)}
EXCLUDED = {"Q": (), "T": ("studies/p10is2/partq/", "studies/p10is2/freeze/")}  # Part T's set is studies/p10is2/** outside partq/; plans and records are never code
ALWAYS = ("uv.lock", "pyproject.toml")
EXTRA_FILES = {"Q": ("studies/p10s2/requirements-datagen.txt",), "T": ()}
LAUNCH_PREFIX = {"Q": "partq_", "T": "partt_"}


def part_config(part: str) -> Path:
    return core.CONFIG_Q if part == "Q" else core.CONFIG_T


def plan_path(part: str) -> Path:
    return core.PLAN_Q if part == "Q" else core.PLAN_T


def record_path(part: str) -> Path:
    return core.FREEZE_RECORD_Q if part == "Q" else core.FREEZE_RECORD_T


def _is_source(p: Path) -> bool:
    return p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"


def frozen_file_hashes(repo: Path, part: str) -> dict[str, str]:
    """SHA-256 of every file of the part's frozen set (section 11 item 2)."""
    out: dict[str, str] = {}
    for root in PART_ROOTS[part]:
        base = repo / root
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            rel = str(p.relative_to(repo))
            if not _is_source(p) or any(rel.startswith(x) for x in EXCLUDED[part]):
                continue
            if "/launch/" in f"/{rel}" and part == "Q" and not p.name.startswith(LAUNCH_PREFIX["Q"]):
                continue  # only the Part Q launch scripts belong to Part Q
            if "/launch/" in f"/{rel}" and part == "T" and p.name.startswith(LAUNCH_PREFIX["Q"]):
                continue
            out[rel] = file_sha256(p)
    if part == "Q":  # the launch scripts of Part Q are in its frozen set (section 11 item 2) although the directory lies outside partq/ and common/
        for p in sorted((repo / "studies/p10is2/launch").glob(LAUNCH_PREFIX["Q"] + "*")):
            if _is_source(p):
                out[str(p.relative_to(repo))] = file_sha256(p)
    for rel in (str(part_config(part)), *ALWAYS, *EXTRA_FILES[part]):
        if (repo / rel).is_file():
            out[rel] = file_sha256(repo / rel)
    return out


def adr_provenance(repo: Path) -> dict[str, str]:
    return {"path": core.SPEC, "sha256": file_sha256(repo / core.SPEC), "note": "provenance only: the ADR text is not a frozen input and no check compares this hash"}


# --- the import walk (section 11 item 2, correction C8) --------------------------------------------------------------------------------------------
_WALK_SCRIPT = r"""
import json, os, sys
repo = os.path.realpath(sys.argv[1])
sys.path.insert(0, repo); sys.path.insert(0, os.path.join(repo, "src"))
opened = set()
def hook(event, args):
    if event == "open" and isinstance(args[0], str):
        try:
            p = os.path.realpath(args[0])
        except Exception:
            return
        if p.startswith(repo + os.sep) and "__pycache__" not in p and "/.venv/" not in p and "/.git/" not in p and not p.endswith(".pyc"):
            opened.add(p)
sys.addaudithook(hook)
import importlib
for m in sys.argv[2:]:
    importlib.import_module(m)
py = set()
for mod in list(sys.modules.values()):
    f = getattr(mod, "__file__", None)
    if f:
        p = os.path.realpath(f)
        if p.startswith(repo + os.sep) and "/.venv/" not in p and p.endswith(".py") and os.path.isfile(p):
            py.add(p)
rel = lambda p: os.path.relpath(p, repo)
print(json.dumps({"python_files": sorted(rel(p) for p in py), "files_opened": sorted(rel(p) for p in opened - py)}))
"""


def entry_modules(repo: Path, part: str) -> list[str]:
    """Every stage module of the part (launch scripts call these): the walk imports them all."""
    mods = []
    for root in PART_ROOTS[part]:
        for p in sorted((repo / root).rglob("*.py")):
            rel = p.relative_to(repo)
            if "__pycache__" in rel.parts or "freeze" in rel.parts or "launch" in rel.parts:
                continue
            if part == "T" and "partq" in rel.parts:
                continue
            mods.append(".".join(rel.with_suffix("").parts).removesuffix(".__init__"))
    return sorted(set(mods))


def import_walk(repo: Path, part: str, modules: Sequence[str] | None = None, timeout: float = 300.0) -> dict[str, Any]:
    """Imports the part's entry modules in a fresh interpreter (isolated mode) with an audit hook and returns the repository files reached: Python files of the modules loaded, and every other repository file
    OPENED during the imports (for P10-S2's modules, ``configs/p10s2_transfer.toml``). Imports only; nothing is run."""
    mods = list(modules) if modules is not None else entry_modules(repo, part)
    proc = subprocess.run([sys.executable, "-I", "-c", _WALK_SCRIPT, str(repo), *mods], capture_output=True, text=True, timeout=timeout, check=False, cwd=repo)  # noqa: S603
    if proc.returncode != 0:
        raise StageRefused(f"the import walk failed: {proc.stderr.strip().splitlines()[-1:]}")
    data = json.loads(proc.stdout.strip().splitlines()[-1])
    own = STUDY_ROOT + "/"
    data["outside_study_python"] = [f for f in data["python_files"] if not f.startswith(own)]
    data["outside_study_data"] = [f for f in data["files_opened"] if not f.startswith(own) and not f.endswith(".py")]
    return data  # type: ignore[no-any-return]


def walk_set(walk: Mapping[str, Any], repo: Path) -> dict[str, str]:
    """Hashes of every file the walk reached outside ``studies/p10is2/``: they join the part's frozen set."""
    return {f: file_sha256(repo / f) for f in sorted({*walk["outside_study_python"], *walk["outside_study_data"]})}


def walk_problems(walk: Mapping[str, Any], listed: Mapping[str, str], repo: Path) -> list[str]:
    """The freeze refuses if the walk reaches a file the set does not list (or lists with another hash)."""
    out = []
    for f, h in walk_set(walk, repo).items():
        if f not in listed:
            out.append(f"the import walk reaches {f}, which the frozen set does not list")
        elif listed[f] != h:
            out.append(f"{f} differs from the frozen hash")
    return out


# --- the plan ------------------------------------------------------------------------------------------------------------------------------
class Plan:
    """The plan file, read only. Every stage derives its items from it."""

    def __init__(self, data: Mapping[str, Any], part: str, path: Path | None = None) -> None:
        if data.get("kind") != "freeze_plan" or data.get("study") != core.STUDY or data.get("schema") != core.SCHEMA or data.get("part") != part:
            raise StageRefused(f"refused: not a P10IS2 Part {part} plan")
        self.data, self.part, self.path = dict(data), part, path

    @classmethod
    def load(cls, path: Path, part: str) -> "Plan":
        if not path.is_file():
            raise StageRefused(f"refused: no freeze plan at {path}: nothing registered runs before the freeze")
        return cls(read_json(path), part, path)

    @property
    def mode(self) -> str:
        return str(self.data["mode"])

    def items(self, stage: str) -> list[dict[str, Any]]:
        if stage not in self.data["items"]:
            raise ValueError(f"unknown stage {stage!r}")
        return list(self.data["items"][stage])

    def cap_seconds(self, stage: str) -> float:
        return float(self.data["stage_caps"][f"{stage}_hours"]) * 3600.0

    def total_cap_seconds(self) -> float:
        return float(self.data["stage_caps"]["total_hours"]) * 3600.0

    def sha256(self) -> str:
        return sha256(canonical_json(self.data))


def build_plan(*, part: str, mode: str, cfg: Mapping[str, Any], repo: Path, items: Mapping[str, list[dict[str, Any]]], run_dir: Path, walk: Mapping[str, Any] | None, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The plan record: a pure function of its inputs (plus the platform block, which is the writing process's own)."""
    if mode not in core.MODES:
        raise ValueError(f"unknown mode {mode!r}")
    frozen = frozen_file_hashes(repo, part)
    if walk is not None:
        frozen.update(walk_set(walk, repo))
    rec: dict[str, Any] = {
        **core.envelope("freeze_plan", part), "mode": mode, "adr": adr_provenance(repo), "config_sha256": file_sha256(repo / part_config(part)), "frozen_files": frozen, "import_walk": None if walk is None else dict(walk),
        "stage_caps": {k: float(v) for k, v in cfg["stage_caps"].items()}, "caps_provisional": bool(cfg["caps"]["provisional"]), "run_dir": str(run_dir.resolve()), "items": {k: list(v) for k, v in items.items()},
        "platform": gates.platform_record(),
        "frozen_input_set": "section 11 item 2: the part's code, config, uv.lock, pyproject.toml, launch scripts, stage caps and listed inputs, plus every file the import walk reaches; the ADR text is not in it",
    }  # fmt: skip
    rec.update(dict(extra or {}))
    return rec


def verify_plan(plan: Plan, repo: Path, run_dir: Path, *, candidate: bool = False) -> None:
    """Every identity the plan recorded must hold now. A difference is PAUSED — IDENTITY (the caller exits with ``IDENTITY_EXIT``)."""
    d, part = plan.data, plan.part
    now = frozen_file_hashes(repo, part)
    walked = {f: h for f, h in d["frozen_files"].items() if f not in now}
    listed_now = {**now, **{f: file_sha256(repo / f) if (repo / f).is_file() else "MISSING" for f in walked}}
    differ = sorted(k for k in set(listed_now) | set(d["frozen_files"]) if listed_now.get(k) != d["frozen_files"].get(k))
    if differ:
        raise StageRefused("refused: frozen file(s) differ from the freeze (PAUSED — IDENTITY): " + ", ".join(differ[:8]))
    if file_sha256(repo / part_config(part)) != d["config_sha256"]:
        raise StageRefused("refused: the config differs from the freeze (PAUSED — IDENTITY)")
    cfg = core.load_config(part, repo / part_config(part))
    section = "stage_caps_attempt3" if (d.get("inputs") or {}).get("reuse") else "stage_caps"  # a plan that reuses completed stages takes its caps from the attempt-3 section
    caps = {k: float(v) for k, v in cfg[section].items()}
    if caps != d["stage_caps"]:
        raise StageRefused("refused: the stage caps in the config differ from the plan's")
    if d["mode"] == REGISTERED and not candidate and (cfg["caps"]["provisional"] or d.get("caps_provisional")):
        raise StageRefused("refused: the caps are provisional: they are computed by code from the measuring rehearsal and set before the freeze (section 10)")
    if Path(d["run_dir"]).resolve() != run_dir.resolve():
        raise StageRefused(f"refused: the freeze names the run directory {d['run_dir']}, not {run_dir}")
    for name, rec in (d.get("manifests") or {}).items():
        p = Path(rec["path"]) if Path(rec["path"]).is_absolute() else repo / rec["path"]
        if not p.is_file() or file_sha256(p) != rec["sha256"]:
            raise StageRefused(f"refused: {p} does not hash to the frozen manifest {name} (PAUSED — IDENTITY)")
    if d["mode"] == REGISTERED and not candidate:
        verify_freeze_record(plan, repo)


# --- registered preconditions ---------------------------------------------------------------------------------------------------------------
def foreign_freeze_records(repo: Path) -> list[str]:
    """Ruling L11: a worktree that another study's freeze record names is not a place to start a registered stage."""
    out = []
    for p in sorted((repo / "studies").glob("*/freeze/*freeze_record*.json")):
        if "p10is2" not in p.parts:
            out.append(str(p.relative_to(repo)))
    return out


def check_preconditions(part: str, mode: str, repo: Path, freeze_commit: str | None, cfg: Mapping[str, Any]) -> dict[str, str] | None:
    """A registered stage refuses unless the working tree is clean, ``freeze_commit`` is an ancestor of HEAD, the part's frozen roots and the config equal their content at that commit, no other study's freeze
    record is in this worktree, and the machine is the platform of record. Returns the freeze identity (None for rehearsal and test)."""
    if mode != REGISTERED:
        return None
    dirty = core.git(repo, "status", "--porcelain", "--untracked-files=all").stdout.decode().rstrip()
    frozen_paths = [*PART_ROOTS[part], *(["studies/p10is2/launch/partq_"] if part == "Q" else []), str(part_config(part)), *ALWAYS, *EXTRA_FILES[part]]
    changed = [ln[3:] for ln in dirty.splitlines() if any(ln[3:].strip('"').startswith(fp) for fp in frozen_paths) and not any(ln[3:].strip('"').startswith(x) for x in EXCLUDED[part])]
    if changed:  # a changed FROZEN file is an identity difference: PAUSED — IDENTITY (exit 75), nothing is written, restoring the file bit for bit resumes the stage
        raise StageRefused("PAUSED — IDENTITY: a frozen file differs from the committed tree: " + ", ".join(changed[:6]))
    if dirty:
        raise StageRefused("refused: the working tree is not clean:\n" + "\n".join(dirty.splitlines()[:10]))
    if not freeze_commit:
        raise StageRefused("refused: a registered stage requires --freeze-commit")
    ok = core.git(repo, "rev-parse", "--verify", "--quiet", f"{freeze_commit}^{{commit}}")
    if ok.returncode != 0:
        raise StageRefused(f"refused: {freeze_commit} is not a commit of this repository")
    full = ok.stdout.decode().strip()
    if core.git(repo, "merge-base", "--is-ancestor", full, "HEAD").returncode != 0:
        raise StageRefused(f"refused: freeze commit {full} is not an ancestor of HEAD")
    launch = [str(p.relative_to(repo)) for p in sorted((repo / "studies/p10is2/launch").glob(LAUNCH_PREFIX["Q"] + "*"))] if part == "Q" else []
    paths = [*PART_ROOTS[part], *launch, str(part_config(part)), *ALWAYS, *EXTRA_FILES[part]]
    problems = [f"PAUSED — IDENTITY: {p} at HEAD differs from the freeze commit" for p in paths if core.git(repo, "rev-parse", f"{full}:{p}").stdout != core.git(repo, "rev-parse", f"HEAD:{p}").stdout]
    if problems:
        raise StageRefused("refused: " + "; ".join(problems))
    foreign = foreign_freeze_records(repo)
    if foreign:
        raise StageRefused("refused: another study's freeze record is in this worktree (ruling L11): " + ", ".join(foreign))
    bad = gates.platform_problems(cfg)
    if bad:
        raise StageRefused("refused: not the platform of record (section 11 item 10): " + "; ".join(bad))
    return {"commit": full, "tree": core.git(repo, "rev-parse", f"{full}^{{tree}}").stdout.decode().strip()}


def require_decision_2(repo: Path, freeze_commit: str, part: str) -> str:
    """Decision 2 for the part is recorded in a COMMITTED file matching the part's glob that holds the line ``DECISION: RUN`` (and not ``DECISION: DO NOT RUN``) and the full freeze commit."""
    pattern = DECISION_2_GLOB[part]
    full = core.git(repo, "rev-parse", "--verify", "--quiet", f"{freeze_commit}^{{commit}}").stdout.decode().strip()
    tracked = [p for p in core.git(repo, "ls-tree", "-r", "--name-only", "HEAD", "--", "results").stdout.decode().split("\n") if fnmatch.fnmatch(p, pattern)]
    for name in tracked:
        text = core.git(repo, "show", f"HEAD:{name}").stdout.decode("utf-8", "replace")  # the committed content, not the working file
        lines = {line.strip() for line in text.splitlines()}
        if full and full in text and DECISION_RUN_LINE in lines and DECISION_NO_RUN_LINE not in lines:
            return name
    raise StageRefused(f"refused: no committed {pattern} contains the line '{DECISION_RUN_LINE}' (and not '{DECISION_NO_RUN_LINE}') and the full freeze commit {full or freeze_commit}: Decision 2 is recorded there before anything registered runs")


def verify_freeze_record(plan: Plan, repo: Path) -> dict[str, Any]:
    """The freeze record (written by ``freeze``) names the SHA-256 of the committed plan file."""
    path = repo / record_path(plan.part)
    if not path.is_file():
        raise StageRefused(f"refused: no freeze record at {path}")
    rec = read_json(path)
    if rec.get("kind") != "freeze_record" or rec.get("plan_file_sha256") != file_sha256(repo / plan_path(plan.part)):
        raise StageRefused("refused: the freeze record does not name the SHA-256 of the committed plan file")
    return dict(rec)


def load_registered_plan(repo: Path, part: str) -> Plan:
    plan = Plan.load(repo / plan_path(part), part)
    if plan.mode != REGISTERED:
        raise StageRefused("refused: the plan in freeze/ is not a registered plan")
    return plan
