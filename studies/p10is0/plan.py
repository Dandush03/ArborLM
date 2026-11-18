# ruff: noqa: E501
"""P10IS0 plan, frozen inputs and preconditions (ADR-0023 sections 10, 14; coordinator rulings 1, 2, 5).

* ``build_plan`` derives the scientific content of the plan from code, config and ``durations.json`` only: the main-grid cells (a cell type removed by the reference rule has none), each with its T, readouts, seed set, initialisation seed.
  Every stage derives its items from the plan file only (``items_of``).
* Frozen inputs (ruling 1): every item is hashed individually by SHA-256: every package file under ``studies/p10is0/``, the config, the launch scripts, ``freeze/plan.json``, ``freeze/durations.json``, ``freeze/stage_caps.json``, the
  sealed files' hashes, and the imported files of ``studies/p10s0``, ``studies/p9ii``, ``studies/p9i`` and ``studies/p9`` (compared with the freeze commit). The identity check iterates over that list, not over a directory.
* Preconditions of a registered entry point: a clean tree, the plan, the freeze record, ``durations.json`` and ``stage_caps.json`` exist, the freeze commit is an ancestor of HEAD, a committed ``results/p10is0-freeze-*/DECISION_2.md``
  names the freeze commit, every frozen input matches its recorded hash, and the run directory is named, git-ignored and not tracked (ruling 2). Nothing is frozen today, so a registered entry point refuses today.
"""

import json
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json

from . import core
from .profile import REGISTERED, Profile

IDENTITY_EXIT = 75
FREEZE_RESULTS_GLOB = "results/p10is0-freeze-*/DECISION_2.md"
PACKAGE = Path("studies/p10is0")
IMPORTED_DIRS = ("studies/p10s0", "studies/p9ii")


class StageRefused(RuntimeError):
    """A precondition is not met: nothing runs and nothing is written."""


class IdentityMismatch(RuntimeError):
    """A frozen input differs from its recorded hash: PAUSED — IDENTITY; restoring the file resumes the task."""


def git(repo: Path, *argv: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(repo), *argv], check=False, capture_output=True)  # noqa: S603, S607


def frozen_paths(repo: Path | None = None, *, include_freeze_files: bool = True) -> list[str]:
    """The frozen-input list (ruling 1), repo-relative and sorted: package files, config, launch scripts, the three freeze files (when they exist), and the imported files of earlier studies."""
    from studies.p9ii import core as p9iicore

    base = repo or core.repo_root()
    out: set[str] = {str(core.CONFIG)}
    for p in sorted((base / PACKAGE).glob("*.py")):
        out.add(f"{PACKAGE}/{p.name}")
    for p in sorted((base / core.LAUNCH_DIR).glob("*.sh")):
        out.add(f"{core.LAUNCH_DIR}/{p.name}")
    if include_freeze_files:
        for rel in (core.PLAN, core.DURATIONS, core.STAGE_CAPS):
            if (base / rel).is_file():
                out.add(str(rel))
    for d in IMPORTED_DIRS:
        for p in sorted((base / d).glob("*.py")):
            out.add(f"{d}/{p.name}")
    for name in p9iicore.IMPORTED_P9I_MODULES:
        out.add(f"studies/p9i/{name}.py")
    for name in p9iicore.IMPORTED_P9_MODULES:
        out.add(f"studies/p9/{name}.py")
    return sorted(out)


def hash_inputs(repo: Path | None = None, paths: Sequence[str] | None = None) -> dict[str, str]:
    """SHA-256 of each listed file individually (nothing is hashed over a directory)."""
    base = repo or core.repo_root()
    return {p: file_sha256(base / p) for p in (paths if paths is not None else frozen_paths(base))}


def committed_hash(repo: Path, commit: str, rel: str) -> str | None:
    import hashlib

    r = git(repo, "show", f"{commit}:{rel}")
    return hashlib.sha256(r.stdout).hexdigest() if r.returncode == 0 else None


def verify_inputs(repo: Path, recorded: Mapping[str, str], freeze_commit: str | None = None) -> list[str]:
    """The differences between the running files and the recorded hashes (iterating over the recorded list), and, for the imported earlier-study files, between the working copy and the freeze commit."""
    problems = []
    for rel, sha in sorted(recorded.items()):
        p = repo / rel
        if not p.is_file():
            problems.append(f"{rel}: missing")
        elif file_sha256(p) != sha:
            problems.append(f"{rel}: differs from the recorded hash")
        if freeze_commit and (rel.startswith(IMPORTED_DIRS) or rel.startswith(("studies/p9i/", "studies/p9/"))):
            if committed_hash(repo, freeze_commit, rel) != sha:
                problems.append(f"{rel}: differs from its content at the freeze commit")
    return problems


def run_dir_problems(run_dir: Path, repo: Path | None = None) -> list[str]:
    """Ruling 2: no TRACKED file of the worktree is written during a run: the run directory is named, git-ignored (under ``experiments/`` in the worktree) or outside the repository, and not tracked."""
    base = (repo or core.repo_root()).resolve()
    run = run_dir.resolve()
    try:
        rel = run.relative_to(base)
    except ValueError:
        return []
    out = []
    if not run_dir.name or run == base:
        out.append("the run directory must be a named directory")
    if git(base, "check-ignore", "-q", str(rel)).returncode != 0:
        out.append(f"{run} is inside the repository and not git-ignored")
    if git(base, "ls-files", "--error-unmatch", str(rel)).returncode == 0:
        out.append(f"{run} is tracked")
    return out


def check_preconditions(repo: Path, run_dir: Path, freeze_commit: str | None) -> dict[str, Any]:
    """Every precondition of a registered entry point; raises ``StageRefused`` (nothing written) or ``IdentityMismatch`` (PAUSED — IDENTITY)."""
    if git(repo, "status", "--porcelain").stdout.strip():
        raise StageRefused("refused: the working tree is not clean")
    for rel in (core.PLAN, core.FREEZE_RECORD, core.DURATIONS, core.STAGE_CAPS):
        if not (repo / rel).is_file():
            raise StageRefused(f"refused: {rel} does not exist (nothing is frozen)")
    if not freeze_commit or git(repo, "merge-base", "--is-ancestor", freeze_commit, "HEAD").returncode != 0:
        raise StageRefused("refused: the freeze commit is missing or not an ancestor of HEAD")
    decisions = [p for p in sorted(repo.glob(FREEZE_RESULTS_GLOB)) if freeze_commit in p.read_text(encoding="utf-8")]
    if not decisions or git(repo, "ls-files", "--error-unmatch", str(decisions[0].relative_to(repo))).returncode != 0:
        raise StageRefused("refused: no committed Decision 2 (results/p10is0-freeze-*/DECISION_2.md) names the freeze commit")
    problems = run_dir_problems(run_dir, repo)
    if problems:
        raise StageRefused("refused: " + "; ".join(problems))
    record = core.read_record(repo / core.FREEZE_RECORD, "freeze_record")
    diffs = verify_inputs(repo, record["inputs"], freeze_commit)
    if diffs:
        raise IdentityMismatch("PAUSED — IDENTITY: " + "; ".join(diffs[:5]))
    return {"freeze_commit": freeze_commit, "decision_2": str(decisions[0].relative_to(repo)), "inputs_checked": len(record["inputs"])}


# --- the plan ----------------------------------------------------------------------------------------------------------------------------
def items_of(plan: Mapping[str, Any], stage: str) -> list[dict[str, Any]]:
    """Every stage derives its items from the plan file only."""
    if stage not in plan["items"]:
        raise ValueError(f"the plan has no stage {stage!r}")
    return list(plan["items"][stage])


def build_plan(
    cfg: Mapping[str, Any], durations: Mapping[str, Mapping[str, Any]], *, caps: Mapping[str, Any] | None = None, profile: Profile = REGISTERED, draw_plan: Mapping[str, Any] | None = None, manifests: Mapping[str, str] | None = None,
    run_dir: str | None = None,
) -> dict[str, Any]:
    """The scientific content of the plan: a pure function of the config, the code, ``durations.json``'s cell types and the draw plan. A cell type removed by the reference rule has no cells; X8 is not in it (its plan is the run
    directory's addendum, section 8). ``profile`` changes only the seed sets, the initialisations and the sizes (the pipeline rehearsal's plan differs from the registered one in those fields and no other: a test diffs them)."""
    th = core.Thresholds.from_config(cfg)
    cells: list[dict[str, Any]] = []
    types: dict[str, Any] = {}
    seed_set_of = {int(k): v for k, v in (draw_plan or {}).get("seed_set_of", {}).items()} or {d: f"p10is0-draw-{d}" for d in range(1, int(cfg["draws"]["registered"]) + 1)}
    for ct in core.cell_types(cfg):
        d = durations.get(ct.name)
        if d is None:
            raise ValueError(f"durations.json has no entry for {ct.name}")
        flags = d.get("reference_flags") or {}
        if flags.get("other"):
            types[ct.name] = {"series": ct.series, "removed": True, "reference_flags": flags}
            continue
        t = int(d["t_exposures"])
        facts = profile.facts_of(ct.facts)
        types[ct.name] = {
            "series": ct.series, "facts": ct.facts, "slots": ct.slots, "load": ct.load, "t_exposures": t, "updates": core.updates_for(t, facts), "floor": ct.floor(th), "arms": list(ct.arms),
            "readouts": sorted({core.updates_for(min(profile.exp(512), t), facts), core.updates_for(t // 2, facts), core.updates_for(t, facts)}), "convergence": d.get("convergence"), "reference_flags": flags,
            "flat_below_floor": bool(d.get("flat_below_floor")), "reference_below_floor_at_t": d.get("reference_below_floor_at_t", []), "extension": d.get("extension"), "labels": d.get("labels", []),
        }  # fmt: skip
        for arm in ct.arms:
            for draw in range(1, int(cfg["draws"]["registered"]) + 1):
                c = core.make_cell("REG", ct, arm, draw, 0, cfg, profile.name)
                spec = core.set_of_name(seed_set_of[draw], cfg, profile.name)
                cells.append({"label": c.label, "cell_type": ct.name, "arm": arm, "draw": draw, "init_seed": c.init_seed, "seed_set": spec.name, "swap_seed": spec.swap_seed(ct.facts, cfg), "updates": core.updates_for(t, facts)})
    return {
        **core.envelope("freeze_plan"), "spec": core.SPEC, "profile": profile.name, "config_sha256": core.config_sha256(), "thresholds": dict(vars(th)), "cell_types": types, "durations_sha256": None,
        "items": {"main": cells}, "draws": {"seed_set_of": {str(k): v for k, v in seed_set_of.items()}, "reserve": [f"p10is0-reserve-{k}" for k in range(1, 5)]}, "draw_manifests": dict(manifests or {}), "run_dir": run_dir,
        "caps": dict(caps or {}), "x8": {"conditional": True, "trigger": "L_Q = 4 after the complete main grid", "addendum": "written to the run directory (section 8)"},
    }  # fmt: skip


SEED_FIELDS = ("init_seed", "seed_set", "swap_seed", "label")


def seed_blind(plan: Mapping[str, Any]) -> dict[str, Any]:
    """The plan with every seed-bearing field, the sizes and the profile removed: two plans built with different profiles must be equal here (stage 2's diff of the plans)."""
    out = {k: v for k, v in plan.items() if k not in ("profile", "draws", "config_sha256", "draw_manifests", "run_dir", "durations_sha256", "caps")}
    out["items"] = {"main": [{k: v for k, v in it.items() if k not in (*SEED_FIELDS, "updates")} for it in plan["items"]["main"]]}
    out["cell_types"] = {n: {k: v for k, v in ct.items() if k not in ("updates", "readouts")} for n, ct in plan["cell_types"].items()}
    return out


def scientific_content(plan: Mapping[str, Any]) -> dict[str, Any]:
    """The plan without the fields the freeze does not compare (the ADR's hash is not a field; the caps are compared by their own file)."""
    return {k: v for k, v in plan.items() if k not in ("caps", "durations_sha256", "stage_r_projection")}


def load_plan(path: Path) -> dict[str, Any]:
    p = read_json(path)
    core.check_envelope(p, "freeze_plan")
    return dict(p)


def write_json_text(obj: Any) -> str:
    return json.dumps(core.jsonable(obj), indent=2, sort_keys=True) + "\n"
