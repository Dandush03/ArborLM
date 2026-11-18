# ruff: noqa: E501
"""P10IS0 sealing of Stage R's output (ADR-0023 section 5.2 (i) to (vi), ruling 18): BY PROCEDURE, not by file permissions.

* Stage R writes accuracies, losses and probe records only under ``<run dir>/sealed/`` (git-ignored, outside version control) through ``write_sealed``; its stdout and logs pass ``validate_public`` (time, memory, shapes, counts,
  identities and ``durations.json`` only) through ``emit``.
* The sha256 of every sealed file is listed by ``sealed_hashes`` for the freeze record.
* ``read_sealed`` is the only reader: it needs the auditor's recomputation script's declared role and records the access; a read by anything else raises, and a disclosed read by the lead voids the blindness claim for that cell
  type (``disclosure_labels``). A committed hash shows the files were not altered, not that nobody read them (section 5.2 limits).
* Selections (plateau, extension, continue) are made by code over in-memory curves, never by a person.
"""

import json
import math
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256

from . import core

SEALED = "sealed"
ACCESS_LOG = "sealed_access_log.jsonl"
ALLOWED_READERS = ("auditor-recomputation", "stage-r-code", "disclose-code")  # the code that makes the selections (resume, plateau) reads its own measurements; no person does
WAVE_LIMIT_SENTENCE = "Stage R's public manifests still show each wave's task count, which shows that some cell type decided or that a run went non-finite, but not which."
LABEL_SEEN = "CALIBRATION VALUES SEEN BY THE LEAD"

PUBLIC_KEYS = frozenset(
    {
        "kind", "schema", "study", "stage", "round", "cell_type", "label", "arm", "calibration_draw", "slots", "facts", "exposures", "updates", "wall_seconds", "seconds_per_update", "peak_rss_bytes", "sampled_rss_bytes", "load_average",
        "shapes", "parameter_counts", "counts", "count", "status", "identity", "environment", "sha256", "path", "decision", "e_star", "t_exposures", "convergence", "flat_below_floor", "extension", "reference_flags", "reference_below_floor_at_t",
        "reference_nonfinite", "nonfinite_in_rehearsal", "removed", "labels", "cell_types", "seed_set", "workers", "tasks", "completed", "cells", "items", "run", "stages", "hashes", "ok", "passed", "reason", "files", "cond4", "other", "evaluation_wall_seconds", "reference_flags_computed", "attempt", "code_identity", "extension_decisions", "projected_hours", "budget_hours", "granted",
    }
)  # fmt: skip
FORBIDDEN_WORDS = ("loss", "acc", "nll", "perplex", "entropy", "margin", "correct", "bits", "m_p", "m_h", "plateau_value", "curve")
# ``durations.json`` carries the words "convergence" and "flat_below_floor" as keys: they are the registered products of section 5.2 (iii). Accuracy-like numbers are what the validator keeps out.


class PublicOutputError(ValueError):
    """An output that would leave the sealed directory contains a key or a value outside the whitelist."""


class SealedRefused(PermissionError):
    """A read of the sealed directory by anything but the auditor's recomputation script (procedural; all sessions share one OS account)."""


def validate_public(obj: Any, *, path: str = "") -> None:
    """Keys must be in ``PUBLIC_KEYS`` (or the cell-type names of ``durations.json``'s ``cell_types`` map); values must be plain: no float that could be an accuracy or loss unless the key is a time, rate, memory or load key."""
    numeric_ok = {"wall_seconds", "evaluation_wall_seconds", "seconds_per_update", "peak_rss_bytes", "sampled_rss_bytes", "load_average", "seconds", "updates", "exposures", "slots", "facts", "t_exposures", "e_star", "round", "calibration_draw", "count", "workers", "schema"}
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            key = str(k)
            in_cell_types = path.endswith("cell_types") or path.endswith("shapes") or path.endswith("parameter_counts") or path.endswith("hashes") or path.endswith("code_identity") or path.endswith("identity") or path.endswith("environment")
            if not in_cell_types and key not in PUBLIC_KEYS:
                raise PublicOutputError(f"key not allowed in a public output: {path}/{key}")
            if any(w in key.lower() for w in FORBIDDEN_WORDS) and key not in ("convergence", "labels"):
                raise PublicOutputError(f"key names a forbidden measure: {path}/{key}")
            validate_public(v, path=f"{path}/{key}")
    elif isinstance(obj, list | tuple):
        for x in obj:
            validate_public(x, path=path)
    elif isinstance(obj, float):
        leaf = path.rsplit("/", 1)[-1]
        if leaf not in numeric_ok and not path.endswith("load_average"):
            raise PublicOutputError(f"a float at {path} is not a time, rate, memory or load figure")
        if not math.isfinite(obj):
            raise PublicOutputError(f"non-finite number at {path}")


def emit(obj: Mapping[str, Any]) -> None:
    """Print a JSON line after the whitelist validator."""
    validate_public(obj)
    print(json.dumps(core.jsonable(dict(obj)), sort_keys=True, ensure_ascii=False))


def repo_common_root(repo: Path) -> Path | None:
    """The main checkout of the repository (the parent of the common repository directory), or None outside a repository."""
    import subprocess

    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--git-common-dir"], capture_output=True, text=True, check=False)  # noqa: S603, S607
    if r.returncode != 0 or not r.stdout.strip():
        return None
    d = Path(r.stdout.strip())
    d = d if d.is_absolute() else (repo / d)
    return d.resolve().parent


def sealed_location_problems(path: Path, repo: Path | None = None) -> list[str]:
    """B1: the sealed directory is refused inside any working tree of a repository (a resolved ancestor holding ``.git``) and anywhere under the repository's main checkout, symlinks resolved. Procedural, not an access control."""
    resolved = path.resolve()
    problems = []
    for anc in [resolved, *resolved.parents]:
        if (anc / ".git").exists():
            problems.append(f"{resolved} is inside the working tree {anc}")
            break
    base = repo or core.repo_root()
    roots = {base.resolve()}
    common = repo_common_root(base)
    if common is not None:
        roots.add(common.resolve())
    for r in roots:
        if resolved == r or r in resolved.parents:
            problems.append(f"{resolved} is under {r}")
    return problems


def disclosed_cell_types(freeze_record: Mapping[str, Any] | None, cell_type_names: Sequence[str]) -> set[str]:
    """R12: the cell types whose sealed files the freeze record says were read by the lead (``disclosed_reads``: file names), or all of them when the seal is declared broken."""
    if not freeze_record:
        return set()
    if freeze_record.get("seal_broken"):
        return set(cell_type_names)
    stems = {n: n.replace("/", "-") + "-" for n in cell_type_names}
    return {n for n, s in stems.items() for f in freeze_record.get("disclosed_reads", []) if str(f).startswith(s)}


def sealed_dir(run_dir: Path) -> Path:
    return run_dir / SEALED


def write_sealed(run_dir: Path, name: str, payload: Mapping[str, Any]) -> Path:
    """The only writer of Stage R's measurements. Refuses a name that leaves the sealed directory and never overwrites."""
    if "/" in name or name.startswith("."):
        raise ValueError("a sealed file name is a plain file name")
    path = sealed_dir(run_dir) / name
    core.write_record(path, {**core.envelope("sealed_eval"), **payload})
    return path


def sealed_hashes(run_dir: Path) -> dict[str, str]:
    """SHA-256 of every sealed file (committed at the freeze); reading a hash opens the bytes for hashing only and returns no value of the record."""
    root = sealed_dir(run_dir)
    return {str(p.relative_to(root)): file_sha256(p) for p in sorted(root.rglob("*")) if p.is_file()} if root.is_dir() else {}


def log_access(run_dir: Path, who: str, what: str, why: str) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / ACCESS_LOG).open("a", encoding="utf-8") as f:
        f.write(json.dumps({"utc": datetime.now(UTC).isoformat(), "who": who, "file": what, "why": why}) + "\n")


def read_sealed(run_dir: Path, name: str, *, reader: str, why: str) -> dict[str, Any]:
    """Only the auditor's recomputation script reads the sealed files. Every read is logged."""
    if reader not in ALLOWED_READERS:
        raise SealedRefused(f"{reader!r} may not read the sealed directory; only the auditor's recomputation script does (ruling 18). A read by the lead is disclosed in the freeze or outcome record and voids the blindness claim")
    log_access(run_dir, reader, name, why)
    return core.read_record(sealed_dir(run_dir) / name, "sealed_eval")


def disclosure_labels(disclosed_cell_types: Sequence[str]) -> dict[str, str]:
    """Every cell type whose sealed file was read by the lead prints CALIBRATION VALUES SEEN BY THE LEAD."""
    return dict.fromkeys(disclosed_cell_types, LABEL_SEEN)
