# ruff: noqa: E501
"""The installed-package manifest of the durable copy of the datagen packages (ADR-0025 section 13 item 6; re-audit R7 and A7).

The durable copy (a directory outside the lock, put on the path for Part Q's real stages only) is described by code: every package's name and version (from its ``*.dist-info/METADATA``), the SHA-256 of every file,
the file count and one tree hash over the sorted (relative path, file hash) pairs. The lock's own packages that the copy SHADOWS (the same distribution name in both; the copy comes first on the path) are recorded
with both versions (A7). The manifest goes into the plan's ``inputs`` block; every stage that uses the packages verifies it at its start, and the freeze refuses a plan without it. Nothing here writes into the
durable copy or imports from it."""

import hashlib
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256

from ..common.core import StageRefused

KEY = "package_manifest"


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def dist_versions(site: Path) -> dict[str, str]:
    """Distribution name (normalised) -> version, from the ``*.dist-info/METADATA`` files of a site directory."""
    out: dict[str, str] = {}
    for meta in sorted(site.glob("*.dist-info/METADATA")):
        name = version = None
        for line in meta.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("Name:") and name is None:
                name = line.split(":", 1)[1].strip()
            elif line.startswith("Version:") and version is None:
                version = line.split(":", 1)[1].strip()
            if name and version:
                break
        if name and version:
            out[_norm(name)] = version
    return out


def file_hashes(root: Path) -> dict[str, str]:
    """Relative path (POSIX) -> SHA-256 of every regular file under ``root`` (symbolic links are refused: a link could point out of the copy)."""
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            raise StageRefused(f"refused: {p} is a symbolic link inside the durable package copy")
        if p.is_file():
            out[p.relative_to(root).as_posix()] = file_sha256(p)
    return out


def tree_sha256(files: Mapping[str, str]) -> str:
    h = hashlib.sha256()
    for k in sorted(files):
        h.update(f"{k}\0{files[k]}\n".encode())
    return h.hexdigest()


def build_manifest(durable_dir: Path, lock_site_packages: Path | None) -> dict[str, Any]:
    """The manifest of ``durable_dir``; ``lock_site_packages`` is the lock environment's site-packages directory (to record the shadowed lock packages), or None to record none."""
    if not durable_dir.is_dir():
        raise StageRefused(f"refused: the durable package copy {durable_dir} is not a directory")
    files = file_hashes(durable_dir)
    packages = dist_versions(durable_dir)
    lock = dist_versions(lock_site_packages) if lock_site_packages is not None else {}
    shadowed = {n: {"durable_version": v, "lock_version": lock[n], "same_version": lock[n] == v} for n, v in sorted(packages.items()) if n in lock}
    return {"path": str(durable_dir), "packages": packages, "file_count": len(files), "tree_sha256": tree_sha256(files), "files": files, "shadowed_lock_packages": shadowed, "lock_site_packages": None if lock_site_packages is None else str(lock_site_packages)}


def verify_manifest(durable_dir: Path, recorded: Mapping[str, Any]) -> None:
    """The durable copy now is the copy the plan recorded: same path, same files with the same hashes, same versions. A difference is ``PAUSED — IDENTITY`` (restoring the copy resumes the stage)."""
    if str(durable_dir) != recorded.get("path"):
        raise StageRefused(f"refused: the durable package copy is at {durable_dir}, the plan recorded {recorded.get('path')} (PAUSED — IDENTITY)")
    files = file_hashes(durable_dir)
    want: Mapping[str, str] = recorded["files"]
    differ = sorted(k for k in set(files) | set(want) if files.get(k) != want.get(k))
    if differ or len(files) != recorded["file_count"] or tree_sha256(files) != recorded["tree_sha256"]:
        raise StageRefused(f"refused: the durable package copy differs from the plan's manifest in {len(differ)} file(s) (PAUSED — IDENTITY): " + ", ".join(differ[:8]))
    if dist_versions(durable_dir) != dict(recorded["packages"]):
        raise StageRefused("refused: the durable package copy's versions differ from the plan's manifest (PAUSED — IDENTITY)")


def require_package_manifest(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """The freeze refuses an inputs block without a well-formed package manifest."""
    m = inputs.get(KEY)
    need = ("path", "packages", "file_count", "tree_sha256", "files", "shadowed_lock_packages")
    if not isinstance(m, dict) or any(k not in m for k in need) or not m["files"] or m["file_count"] != len(m["files"]) or tree_sha256(m["files"]) != m["tree_sha256"]:
        raise StageRefused("refused: the plan's inputs block has no well-formed installed-package manifest (names, versions, file hashes, shadowed lock packages): produce it with the package-manifest command")
    return dict(m)


def verify_inputs(inputs: Mapping[str, Any], *, uses_packages: bool, repo: Path | None = None) -> None:
    """Stage start: every file input of the plan's ``inputs`` block (entries with a path and a SHA-256, which is the file's real SHA-256: an upstream checksum of another kind is kept under ``upstream_checksum``) still has its hash, and for a stage that uses the packages the durable copy still matches its manifest."""
    for name, rec in sorted(inputs.items()):
        if name == "reuse" and isinstance(rec, dict) and "source_run_dir" in rec:
            from . import reuse

            reuse.verify_block(rec)  # the reused stages' files of the earlier attempt, byte for byte (condition 1 of the attempt-3 addendum)
            continue
        if name == KEY or not isinstance(rec, dict) or "sha256" not in rec or "path" not in rec:
            continue
        p = Path(rec["path"])
        if not p.is_absolute():  # a repository file is stored repo-relative and resolved against the repository the stage runs from
            if repo is None:
                raise StageRefused(f"refused: input {name!r} has a repository-relative path and no repository was given")
            p = repo / p
        if not p.is_file() or file_sha256(p) != rec["sha256"]:
            raise StageRefused(f"refused: input {name!r} ({p}) is missing or differs from the plan's hash (PAUSED — IDENTITY)")
    if uses_packages:
        verify_manifest(Path(require_package_manifest(inputs)["path"]), inputs[KEY])
