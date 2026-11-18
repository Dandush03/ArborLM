# ruff: noqa: E501
"""P10IS5 plan, freeze identity and registered preconditions (ADR-0028 section 12; the pattern of ADR-0029 section 13).

``freeze/plan.json`` holds DEFINITIONS, not outputs: the registered and the counting-rehearsal geometries, the seeds, the cells, n(s), the tiling rule, the file paths. It does not hold m_t, the quiet figures, request lists or any
measured value (those are in the config, written from R1's and M's records BEFORE the plan, or are written by stage P after the freeze). Every stage derives its passes from the plan file only (``Plan.registered_geometry``,
``Plan.blocks``); nothing the counting rehearsal produces is inside the file it rehearses.

The frozen-input set is the ADR's list: ``studies/p10is5/**`` (code, launch scripts, freeze files other than the plan itself and the freeze record), the config (which holds every threshold), ``freeze/plan.json``, the stage caps,
and R1's and M's records (identity by SHA-256). The ADR text is not in it: its hash is stored for provenance only and no check compares it. Imported code of earlier studies (here ``src/arborlm``, ``uv.lock`` and
``pyproject.toml``) is compared between the freeze commit and HEAD.

Registered entry points refuse (``check_preconditions``, ``Plan.load``, ``verify_plan``, ``require_decision_2``) unless the tree is clean, the freeze commit is an ancestor of HEAD, the frozen files equal their content at
that commit, the plan and the freeze record exist and every identity in it holds, and a committed Decision 2 names the freeze commit. Nothing is frozen today, so they refuse today.
"""

import fnmatch
import platform
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import canonical_json, file_sha256, read_json, sha256

from . import core
from .core import Geometry, StageRefused

REGISTERED_STAGES = ("e1", "p", "e2", "analysis", "report", "delete")
FREEZE_RECORD = core.FREEZE_DIR / "freeze_record.json"
IMPORTED_CODE_PATHS = ("src/arborlm", "uv.lock", "pyproject.toml")
DECISION_2_GLOB = "results/p10is5-freeze-*/DECISION_2.md"
DECISION_RUN_LINE = "DECISION: RUN"
DECISION_NO_RUN_LINE = "DECISION: DO NOT RUN"
FROZEN_ROOTS = ("studies/p10is5",)
TILING_RULE = (
    "One seeded permutation (torch.randperm, Generator.manual_seed(assignment seed)) of the usable tiles assigns tiles to (repeat, k, s) in the order repeat, k = 1,2,4,8,16,32, s = 1,3,8,64, taking the tiles-per-pass count of each size; "
    "a tile given to size s is cut into floor(64 / s) aligned, non-overlapping segments from its start; the pass's segments, listed by (tile position in the deal, segment index), are permuted by torch.randperm with the generator "
    "seeded by the first 8 bytes of SHA-256('p10is5|order|<repeat seed>|<k>|<s>') modulo 2**63 and the first n(s) are used; request j goes to thread j mod k; the pass order is torch.randperm(24) of the k-major cells"
)  # fmt: skip


def git(repo: Path, *argv: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(repo), *argv], capture_output=True, check=False)  # noqa: S603, S607


# --- frozen-input hashes -------------------------------------------------------------------------------------------------------------------------
def frozen_file_hashes(repo: Path) -> dict[str, str]:
    """SHA-256 of every file of ``studies/p10is5/**`` (``__pycache__`` is not a source; ``freeze/plan.json`` and the freeze record are hashed separately) and of the config. The ADR is not here."""
    out: dict[str, str] = {}
    for root in FROZEN_ROOTS:
        for p in sorted((repo / root).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc" and p not in (repo / core.PLAN, repo / FREEZE_RECORD) and "superseded" not in p.parts:
                out[str(p.relative_to(repo))] = file_sha256(p)
    out[str(core.CONFIG)] = file_sha256(repo / core.CONFIG)
    return out


def adr_provenance(repo: Path) -> dict[str, str]:
    return {"path": core.SPEC, "sha256": file_sha256(repo / core.SPEC), "note": "provenance only: the ADR text is not a frozen input and no check compares this hash"}


# --- geometry <-> plan --------------------------------------------------------------------------------------------------------------------------
def geometry_to_json(g: Geometry) -> dict[str, Any]:
    return {"name": g.name, "file_tiles": g.file_tiles, "usable_tiles": g.usable_tiles, "sizes": list(g.sizes), "depths": list(g.depths), "requests_per_pass": list(g.requests), "tiles_per_pass": list(g.tiles), "repeats": g.repeats, "has_spare": g.has_spare}


def geometry_from_json(d: Mapping[str, Any]) -> Geometry:
    return Geometry(str(d["name"]), int(d["file_tiles"]), int(d["usable_tiles"]), tuple(map(int, d["sizes"])), tuple(map(int, d["depths"])), tuple(map(int, d["requests_per_pass"])), tuple(map(int, d["tiles_per_pass"])), int(d["repeats"]), bool(d["has_spare"]))


def block_definitions(cfg: Mapping[str, Any], which: str) -> list[dict[str, Any]]:
    """One definition per repeat: the repeat number, whether it is the spare, the request-order seed and the pass-order seed. ``which`` is ``registered`` or ``k`` (the counting rehearsal)."""
    s = cfg["seeds"]
    if which == "registered":
        req, order, spare = list(s["request_order"]), list(s["pass_order"]), True
        req_spare, order_spare = int(s["spare_request_order"]), int(s["spare_pass_order"])
    elif which == "k":
        req, order, spare = list(s["k_request_order"]), list(s["k_pass_order"]), False
        req_spare = order_spare = 0
    else:
        raise ValueError(f"unknown block set {which!r}")
    blocks = [{"repeat": i + 1, "role": "regular", "request_order_seed": int(req[i]), "pass_order_seed": int(order[i])} for i in range(len(req))]
    if spare:
        blocks.append({"repeat": len(req) + 1, "role": "spare", "request_order_seed": req_spare, "pass_order_seed": order_spare})
    return blocks


def plan_content(cfg: Mapping[str, Any], data_dir: Path) -> dict[str, Any]:
    """The scientific content of the plan: definitions only. A pure function of the config and the data directory (``freeze`` re-derives it and refuses any difference)."""
    reg, reh = core.registered_geometry(cfg), core.rehearsal_geometry(cfg)
    s, d = cfg["seeds"], cfg["device"]
    return {
        "geometries": {"registered": geometry_to_json(reg), "rehearsal": geometry_to_json(reh)},
        "cells": [{"k": k, "s": sz, "n_registered": reg.n_of[sz], "tiles_registered": reg.tiles_of[sz], "n_rehearsal": reh.n_of[sz], "tiles_rehearsal": reh.tiles_of[sz]} for k, sz in reg.cells()],
        "tiling_rule": TILING_RULE,
        "registered": {"file_contents_seed": int(s["store_contents"]), "tile_assignment_seed": int(s["tile_assignment"]), "blocks": block_definitions(cfg, "registered"), "tiles_dealt": reg.tiles_needed(), "page_bytes": int(d["page_bytes"]), "tile_pages": int(d["tile_pages"])},
        "counting_rehearsal": {"file_contents_seed": int(s["r1_rehearsal_file_contents"]), "tile_assignment_seed": int(s["k_tile_assignment"]), "blocks": block_definitions(cfg, "k"), "tiles_dealt": reh.tiles_needed()},
        "paths": {"data_dir": str(data_dir), "store": str(data_dir / "store.bin"), "rehearsal_file": str(data_dir / "rehearsal.bin"), "control_file": str(data_dir / "control.bin")},
        "files": {"store_tiles": int(d["store_tiles"]), "rehearsal_tiles": int(d["rehearsal_tiles"]), "control_tiles": int(d["control_tiles"]), "control_contents_seed": int(s["r1_control_file_contents"]), "harness": {"requests": int(cfg["thresholds"]["harness_requests"]), "tiles": int(cfg["thresholds"]["harness_tiles"]), "depths": list(cfg["thresholds"]["harness_depths"])}},
    }  # fmt: skip


def platform_record() -> dict[str, Any]:
    import torch

    return {
        "system": platform.system(), "machine": platform.machine(), "release": platform.release(), "python": platform.python_version(), "torch": torch.__version__,
        "torch_num_threads": torch.get_num_threads(), "torch_interop_threads": torch.get_num_interop_threads(), "deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled()),
    }  # fmt: skip


def platform_problems(cfg: Mapping[str, Any], record: Mapping[str, Any] | None = None) -> list[str]:
    """What differs from the platform of record: macOS arm64, CPython 3.12, torch 2.8.0, one thread, one interop thread, deterministic algorithms on."""
    want = cfg["platform"]
    have = record or platform_record()
    problems = []
    for k_have, k_want in (("system", "system"), ("machine", "machine"), ("torch_num_threads", "torch_num_threads"), ("torch_interop_threads", "torch_interop_threads"), ("deterministic_algorithms", "deterministic_algorithms")):
        if have[k_have] != want[k_want]:
            problems.append(f"{k_have}: {have[k_have]!r}, the platform of record has {want[k_want]!r}")
    if str(have["torch"]).split("+")[0] != want["torch"]:
        problems.append(f"torch: {have['torch']!r}, the platform of record has {want['torch']!r}")
    if not str(have["python"]).startswith(str(want["python_prefix"])):
        problems.append(f"python: {have['python']!r}, the platform of record has {want['python_prefix']!r}.x")
    return problems


def file_ref(path: Path) -> dict[str, str]:
    return {"path": str(path.resolve()), "sha256": file_sha256(path)}


def build_plan(cfg: Mapping[str, Any], repo: Path, data_dir: Path, run_dir: Path, records: Mapping[str, Path]) -> dict[str, Any]:
    """The candidate plan record. Identity of every frozen file and the config, the caps, the run directory, R1's and M's records (``records``: name -> path), and the definitions of ``plan_content``."""
    return {
        **core.envelope("freeze_plan"), "mode": "registered", "adr": adr_provenance(repo), "config_sha256": core.config_sha256(repo / core.CONFIG), "frozen_files": frozen_file_hashes(repo),
        "stage_caps": {k: float(v) for k, v in cfg["caps"].items() if k.endswith("_hours")}, "caps_provisional": bool(cfg["caps"]["provisional"]), "figures_provisional": core.provisional_figures(cfg),
        "run_dir": str(run_dir.resolve()), "records": {name: file_ref(p) for name, p in sorted(records.items())}, "platform": platform_record(),
        "content": plan_content(cfg, data_dir.resolve()),
        "frozen_input_set": "studies/p10is5/** (code, launch scripts, freeze files other than the plan and the freeze record), the config, freeze/plan.json, stage caps, R1's and M's records; the ADR text is not in it",
    }  # fmt: skip


NOT_COMPARED = ("adr", "platform")  # the ADR is recorded for provenance only (section 12); the platform block is the freezing process's own


def scientific_content(plan_data: Mapping[str, Any]) -> dict[str, Any]:
    """The plan without the ADR's hash and the process platform record: what the freeze's re-derivation compares."""
    return {k: v for k, v in plan_data.items() if k not in NOT_COMPARED}


class Plan:
    """The plan file, read only. Geometry, seeds and paths come from the file; ``Plan`` never looks at the config."""

    def __init__(self, data: Mapping[str, Any], path: Path | None = None) -> None:
        if data.get("kind") != "freeze_plan" or data.get("study") != core.STUDY or data.get("schema") != core.SCHEMA:
            raise StageRefused("refused: not a P10IS5 plan")
        self.data, self.path = dict(data), path

    @classmethod
    def load(cls, path: Path) -> "Plan":
        if not path.is_file():
            raise StageRefused(f"refused: no freeze plan at {path}: nothing registered runs before the freeze")
        return cls(read_json(path), path)

    @property
    def content(self) -> dict[str, Any]:
        return dict(self.data["content"])

    def geometry(self, which: str) -> Geometry:
        return geometry_from_json(self.content["geometries"][which])

    def blocks(self, which: str) -> list[dict[str, Any]]:
        key = "registered" if which == "registered" else "counting_rehearsal"
        return [dict(b) for b in self.content[key]["blocks"]]

    def section(self, which: str) -> dict[str, Any]:
        return dict(self.content["registered" if which == "registered" else "counting_rehearsal"])

    @property
    def paths(self) -> dict[str, str]:
        return dict(self.content["paths"])

    def cap_seconds(self, stage_name: str) -> float:
        return float(self.data["stage_caps"][f"{stage_name}_hours"]) * 3600.0

    def total_cap_seconds(self) -> float:
        return float(self.data["stage_caps"]["total_hours"]) * 3600.0

    def sha256(self) -> str:
        return sha256(canonical_json(self.data))


def verify_plan(plan: Plan, repo: Path, run_dir: Path, *, candidate: bool = False) -> None:
    """Every identity the plan recorded must hold now: the frozen files and the config (SHA-256), the caps (not provisional, equal to the config's), the figures (not provisional), R1's and M's records, the run directory,
    and the plan's content equal to a re-derivation from the config. ``candidate`` skips the freeze-record check (K runs against the candidate plan before the freeze)."""
    d = plan.data
    now = frozen_file_hashes(repo)
    differ = sorted(k for k in set(now) | set(d["frozen_files"]) if now.get(k) != d["frozen_files"].get(k))
    if differ:
        raise StageRefused(f"refused: frozen file(s) differ from the freeze ({core.PAUSED_IDENTITY}): " + ", ".join(differ[:8]))
    if core.config_sha256(repo / core.CONFIG) != d["config_sha256"]:
        raise StageRefused(f"refused: the config differs from the freeze ({core.PAUSED_IDENTITY})")
    cfg = core.load_config(repo / core.CONFIG)
    caps = {k: float(v) for k, v in cfg["caps"].items() if k.endswith("_hours")}
    if caps != d["stage_caps"]:
        raise StageRefused("refused: the stage caps in the config differ from the plan's")
    if core.caps_provisional(cfg) or d.get("caps_provisional"):
        raise StageRefused("refused: the caps are provisional: the lead sets them after M (charged hours + 2 x projected remaining) and the plan is rewritten")
    if core.provisional_figures(cfg) or d.get("figures_provisional"):
        raise StageRefused("refused: m_t and the quiet figures are provisional: they are written into the config from R1's and M's records before the candidate plan")
    if Path(d["run_dir"]).resolve() != run_dir.resolve():
        raise StageRefused(f"refused: the freeze names the run directory {d['run_dir']}, not {run_dir}")
    for name, ref in (d.get("records") or {}).items():
        p = Path(ref["path"])
        if not p.is_file() or file_sha256(p) != ref["sha256"]:
            raise StageRefused(f"refused: {p} does not hash to the frozen record {name} ({core.PAUSED_IDENTITY})")
    if d["content"] != plan_content(cfg, Path(d["content"]["paths"]["data_dir"])):
        raise StageRefused("refused: the plan's content differs from a re-derivation from the config")
    if not candidate:
        verify_freeze_record(plan, repo)


def check_preconditions(repo: Path, freeze_commit: str | None, cfg: Mapping[str, Any] | None = None) -> dict[str, str]:
    """A registered stage refuses unless the working tree is clean, ``freeze_commit`` is an ancestor of HEAD, ``studies/p10is5``, the config and the imported code equal their content at that commit and the machine
    is the platform of record. Returns the freeze identity."""
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
    paths = (*FROZEN_ROOTS, *IMPORTED_CODE_PATHS, str(core.CONFIG))
    problems = [f"{p} at HEAD differs from the freeze commit" for p in paths if git(repo, "rev-parse", f"{full}:{p}").stdout != git(repo, "rev-parse", f"HEAD:{p}").stdout]
    if problems:
        raise StageRefused("refused: " + "; ".join(problems))
    bad = platform_problems(cfg or core.load_config(repo / core.CONFIG))
    if bad:
        raise StageRefused("refused: not the platform of record (section 12): " + "; ".join(bad))
    return {"commit": full, "tree": git(repo, "rev-parse", f"{full}^{{tree}}").stdout.decode().strip()}


def require_ignored_run_dir(repo: Path, run_dir: Path) -> None:
    """A run directory inside the repository must be git-ignored: otherwise the first record makes the tree dirty and every later worker refuses. A directory outside the repository cannot dirty it."""
    try:
        rel = run_dir.resolve().relative_to(repo.resolve())
    except ValueError:
        return
    if git(repo, "check-ignore", "-q", str(rel) + "/x").returncode != 0:
        raise StageRefused(f"refused: the run directory {run_dir} is inside the repository and is not git-ignored")


def require_data_dir_outside(repo: Path, data_dir: Path, suffix: str = ".noindex", home: Path | None = None) -> None:
    """Section 6: the file directory's name ends in ``.noindex`` and lies outside every git worktree (and so inside no synced folder of the repository)."""
    if not data_dir.name.endswith(suffix):
        raise StageRefused(f"refused: the file directory {data_dir} does not end in {suffix}")
    resolved = data_dir.resolve()
    home = (home or Path.home()).resolve()
    if home not in (resolved, *resolved.parents):
        raise StageRefused(f"refused: the file directory {data_dir} is not under the home folder {home}")
    synced = ("Mobile Documents", "CloudStorage", "iCloud", "Dropbox", "OneDrive", "Google Drive", "Box")
    if any(part.startswith(synced) for part in resolved.parts) or (resolved.parent.name in ("Desktop", "Documents") and resolved.parent.parent == home and (home / "Library" / "Mobile Documents").exists()):
        raise StageRefused(f"refused: the file directory {data_dir} is in a synced folder (iCloud or another sync client)")
    for parent in (resolved, *resolved.parents):
        if (parent / ".git").exists():
            raise StageRefused(f"refused: the file directory {data_dir} is inside a git worktree ({parent})")


def require_decision_2(repo: Path, freeze_commit: str) -> str:
    """Decision 2 is recorded in a committed file ``results/p10is5-freeze-*/DECISION_2.md`` holding the line ``DECISION: RUN`` (and not ``DECISION: DO NOT RUN``) and the full freeze commit."""
    full = git(repo, "rev-parse", "--verify", "--quiet", f"{freeze_commit}^{{commit}}").stdout.decode().strip()
    tracked = [p for p in git(repo, "ls-tree", "-r", "--name-only", "HEAD", "--", "results").stdout.decode().split("\n") if fnmatch.fnmatch(p, DECISION_2_GLOB)]
    for name in tracked:
        text = git(repo, "show", f"HEAD:{name}").stdout.decode("utf-8", "replace")  # the committed content, not the working file
        lines = {line.strip() for line in text.splitlines()}
        if full and full in text and DECISION_RUN_LINE in lines and DECISION_NO_RUN_LINE not in lines:
            return name
    raise StageRefused(f"refused: no committed {DECISION_2_GLOB} contains the line '{DECISION_RUN_LINE}' (and not '{DECISION_NO_RUN_LINE}') and the full freeze commit {full or freeze_commit}: Decision 2 is recorded there before anything registered runs")


def verify_freeze_record(plan: Plan, repo: Path) -> dict[str, Any]:
    """The freeze record (written by the ``freeze`` command, hashed with the other frozen files) names the SHA-256 of the committed ``plan.json`` file and of the counting-rehearsal record that rehearsed that file."""
    path = repo / FREEZE_RECORD
    if not path.is_file():
        raise StageRefused(f"refused: no freeze record at {path}")
    rec = read_json(path)
    if rec.get("kind") != "freeze_record" or rec.get("plan_file_sha256") != file_sha256(repo / core.PLAN):
        raise StageRefused("refused: the freeze record does not name the SHA-256 of the committed plan.json")
    return dict(rec)


def load_registered_plan(repo: Path) -> Plan:
    plan = Plan.load(repo / core.PLAN)
    if plan.data.get("mode") != "registered":
        raise StageRefused("refused: the plan in freeze/ is not a registered plan")
    return plan


def stages_refusing_reasons(stage: str, repo: Path, run_dir: Path, freeze_commit: str | None) -> Sequence[str]:
    """Everything a registered stage checks, in order, as a list of the first refusal (for the entry point): preconditions, plan, identity, Decision 2. Raises ``StageRefused``."""
    if stage not in REGISTERED_STAGES:
        raise ValueError(f"unknown registered stage {stage!r}")
    cfg = core.load_config(repo / core.CONFIG)
    check_preconditions(repo, freeze_commit, cfg)
    assert freeze_commit is not None
    plan = load_registered_plan(repo)
    require_ignored_run_dir(repo, run_dir)
    verify_plan(plan, repo, run_dir)
    require_decision_2(repo, freeze_commit)
    return ["ok"]
