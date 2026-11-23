# ruff: noqa: E501
"""P10-I-S2 Part T, cap amendment (ruling 51; ``AMENDMENT_NOTES.md`` lists every departure from ADR-0025).

Cost-projected stage caps replace the 2 x rule for the stages the config names in ``[cap_amendment]``, and only while an AMENDMENT RECORD names exactly those keys. The record is a committed file, pinned by SHA-256
in the plan's manifests; it also names the ``studies/p10is2/*.py`` files exempt from the freeze's comparison with the calibration record (the files that hold the cap arithmetic and that comparison, never a training or
scoring file: ``PROTECTED``). Calibration is not repeated and its selections do not change. With no ``[cap_amendment]`` section nothing here changes any behaviour.
"""

import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json

from ..common.core import StageRefused

KIND = "cap_amendment_record"
PROTECTED = (  # training, scoring, labels and calibration code: never exempt from the calibration record's hash comparison
    "studies/p10is2/engine.py", "studies/p10is2/partt_run.py", "studies/p10is2/scoring.py", "studies/p10is2/labels.py", "studies/p10is2/annotations.py",
    "studies/p10is2/partt_items.py", "studies/p10is2/partt_real.py", "studies/p10is2/calibration.py", "studies/p10is2/quantities.py",
)  # fmt: skip
STAGE_KEYS = ("gates_hours", "train_hours", "evaluate_hours", "controls_hours", "combined_hours", "recompute_hours", "analysis_hours", "report_hours")


def load(cfg: Mapping[str, Any], repo: Path) -> dict[str, Any] | None:
    """The amendment in force, or None when the config has no ``[cap_amendment]`` section. Refuses unless the record exists, is of the right kind, names exactly the config's cap keys, and exempts no protected file."""
    section = cfg.get("cap_amendment")
    if not section:
        return None
    rel = str(section.get("record", ""))
    path = repo / rel
    if not rel or not path.is_file():
        raise StageRefused(f"refused: [cap_amendment] names the record {rel!r}, which does not exist: an amended cap is accepted only when an amendment record names it")
    rec = read_json(path)
    if rec.get("kind") != KIND:
        raise StageRefused(f"refused: {rel} is not a {KIND}")
    caps = {k: float(v) for k, v in section.items() if k not in ("record", "targeted_allowance_hours")}
    bad = [k for k in caps if k not in STAGE_KEYS]
    if bad:
        raise StageRefused(f"refused: [cap_amendment] holds keys that are not registered stage caps: {bad}")
    allowance = float(section.get("targeted_allowance_hours", 0.0))
    if allowance <= 0.0:
        raise StageRefused("refused: [cap_amendment] needs targeted_allowance_hours > 0 (the charged-hour allowance of the targeted rehearsal, fixed before it runs)")
    if set(caps) != set(rec.get("stage_cap_keys", [])):
        raise StageRefused(f"refused: the config's amended caps {sorted(caps)} are not the keys the amendment record names {sorted(rec.get('stage_cap_keys', []))}")
    if any(v <= 0.0 for v in caps.values()):
        raise StageRefused("refused: an amended cap is never 0 or negative")
    exempt = [str(f) for f in rec.get("exempt_files", [])]
    wrong = [f for f in exempt if f in PROTECTED or not (f.startswith("studies/p10is2/") and f.endswith(".py"))]
    if wrong:
        raise StageRefused(f"refused: the amendment record exempts files that may not be exempt (training, scoring, labels, calibration or not a studies/p10is2 .py file): {wrong}")
    return {"caps": caps, "allowance_hours": allowance, "exempt_files": exempt, "record": {"path": rel, "sha256": file_sha256(path)}, "first_freeze_commit": str(rec.get("first_freeze_commit", "")), "pre_amendment_plan_sha256": str(rec.get("pre_amendment_plan_sha256", "")), "allowed_config_paths": list(rec.get("allowed_config_paths", []))}


def apply(proposal: Mapping[str, float], amend: Mapping[str, Any] | None, charge_seconds: float, allowance_seconds: float) -> dict[str, float]:
    """The proposal with the amended stage caps, and the total recomputed as the charge before the freeze + the counting allowance + the sum of the stage caps, hours rounded up to 0.01 h (as the 2 x rule's total, with the
    stage caps as they are). Unchanged when there is no amendment."""
    out = {k: float(v) for k, v in proposal.items()}
    if not amend:
        return out
    for k, v in amend["caps"].items():
        if k not in out:
            raise StageRefused(f"refused: the amendment names the cap {k!r}, which the proposal does not carry")
        out[k] = float(v)
    stage_seconds = sum(v for k, v in out.items() if k in STAGE_KEYS) * 3600.0
    out["total_hours"] = math.ceil((float(charge_seconds) + float(allowance_seconds) + stage_seconds) / 3600.0 * 100.0 - 1e-9) / 100.0
    return out


def checked_files(files: Sequence[str], amend: Mapping[str, Any] | None) -> list[str]:
    """The ``studies/p10is2/*.py`` files the freeze compares with the calibration record: all of them, less the files the amendment record exempts."""
    skip = set(amend["exempt_files"]) if amend else set()
    return [f for f in files if f not in skip]


def manifest_problem(plan_manifests: Mapping[str, Any] | None, amend: Mapping[str, Any] | None, repo: Path) -> str | None:
    """With an amendment, the plan names its record by path and SHA-256 under ``cap_amendment_record`` (every registered stage re-hashes the manifests)."""
    if not amend:
        return None
    m = (plan_manifests or {}).get("cap_amendment_record")
    if not m or m.get("path") != amend["record"]["path"] or m.get("sha256") != amend["record"]["sha256"] or file_sha256(repo / amend["record"]["path"]) != m.get("sha256"):
        return "the plan does not list cap_amendment_record by the path and SHA-256 of the amendment record now in force (candidate-plan --manifests)"
    return None


REQUIRED_CHECKS = ("preflight", "m_ii_alone_at_registered_size", "cap_stop_and_resume_from_checkpoint", "charged_time_cap_refused_once", "memory_admission_refused_once")


def differing_paths(a: Any, b: Any, path: str = "") -> list[str]:
    """The paths at which two parsed values differ (a key present in one only counts)."""
    if isinstance(a, dict) and isinstance(b, dict):
        out: list[str] = []
        for k in sorted(set(a) | set(b)):
            out += [f"{path}.{k}"] if (k not in a or k not in b) else differing_paths(a[k], b[k], f"{path}.{k}")
        return out
    return [] if a == b else [path or "."]


def plan_diff_problems(old: Mapping[str, Any], new: Mapping[str, Any], amend: Mapping[str, Any], config_rel: str = "configs/p10is2_partt.toml") -> list[str]:
    """The amended plan differs from the plan the first counting rehearsal completed against in ONLY: the amended stage caps and the total, the config hash, the counting (targeted) allowance and the charge before the
    freeze, the amendment record's manifest entry, and the hashes of the config, the exempt files and the amendment's own files (with their names in the import walk). Anything else is listed."""
    ok_exact = {".config_sha256", ".counting_allowance_hours", ".charge_before_freeze", ".manifests.cap_amendment_record", ".stage_caps.total_hours"} | {f".stage_caps.{k}" for k in amend["caps"]}
    ok_files = {f".frozen_files.{f}" for f in [*amend["exempt_files"], config_rel]}
    own = "studies/p10is2/partt_amendment/"
    out = []
    for d in differing_paths(dict(old), dict(new)):
        if d in ok_exact or d in ok_files or d.startswith(f".frozen_files.{own}") or d.startswith(".charge_before_freeze"):
            continue
        if d in (".import_walk.python_files", ".import_walk.files_opened"):
            key = d.rsplit(".", 1)[1]
            changed = set(map(str, old["import_walk"][key])) ^ set(map(str, new["import_walk"][key]))
            if all(own in c or c in amend["exempt_files"] for c in changed):  # the amendment's own directory and its exempt files (the targeted rehearsal's module)
                continue
        out.append(d)
    return out


def config_diff_problems(old: Mapping[str, Any], new: Mapping[str, Any], amend: Mapping[str, Any]) -> list[str]:
    """The config differs from the first freeze's only at the paths the amendment record lists (the bound, the M-ii worker count, the admission threshold), the amended and total stage caps and the ``cap_amendment`` section."""
    ok = {f".stage_caps.{k}" for k in amend["caps"]} | {".stage_caps.total_hours"} | set(amend["allowed_config_paths"])
    return [d for d in differing_paths(dict(old), dict(new)) if d not in ok and not d.startswith(".cap_amendment")]


def targeted_gate(record: Mapping[str, Any] | None, plan_file_sha256: str) -> dict[str, Any]:
    """The targeted rehearsal's record: COMPLETE, against THIS plan file, with every required check passed."""
    if record is None:
        return {"passed": False, "reason": "no targeted rehearsal record"}
    checks = record.get("checks") or {}
    failed = [c for c in REQUIRED_CHECKS if (checks.get(c) or {}).get("passed") is not True]
    ok = record.get("kind_of_rehearsal") == "targeted" and record.get("status") == "COMPLETE" and record.get("plan_file_sha256") == plan_file_sha256 and record.get("caps_provisional") is False and not failed
    return {"passed": bool(ok), "failed_checks": failed, "plan_file_hash_matches": record.get("plan_file_sha256") == plan_file_sha256, "kind": record.get("kind_of_rehearsal"), "status": record.get("status")}


def freeze_problems(repo: Path, cfg: Mapping[str, Any], plan_data: Mapping[str, Any], amend: Mapping[str, Any]) -> list[str]:
    """What the second freeze checks about the amendment: the first freeze commit's plan hashes to the one the record names and differs from this plan only as ``plan_diff_problems`` allows; the first freeze commit's
    config differs from this config only as ``config_diff_problems`` allows. Read-only (version control is only read)."""
    import hashlib
    import subprocess
    import tomllib

    commit = amend["first_freeze_commit"]
    if not commit or len(commit) != 40:
        return ["the amendment record names no first freeze commit"]

    def show(rel: str) -> bytes:
        r = subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{rel}"], capture_output=True, check=False, timeout=60)  # noqa: S603, S607
        if r.returncode != 0:
            raise StageRefused(f"refused: {rel} is not in the first freeze commit {commit}")
        return r.stdout

    import json

    old_plan_bytes = show("studies/p10is2/freeze/partt_plan.json")
    out: list[str] = []
    if hashlib.sha256(old_plan_bytes).hexdigest() != amend["pre_amendment_plan_sha256"]:
        out.append("the plan at the first freeze commit is not the pre-amendment plan the amendment record names")
    out += [f"plan differs at {d}" for d in plan_diff_problems(json.loads(old_plan_bytes), plan_data, amend)]
    out += [f"config differs at {d}" for d in config_diff_problems(tomllib.loads(show("configs/p10is2_partt.toml").decode("utf-8")), dict(cfg), amend)]
    return out
