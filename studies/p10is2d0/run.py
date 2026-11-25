# ruff: noqa: E501
"""P10-I-S2-D0 driver pieces (ADR-0035 sections 3, 8, 10, 11): file lists with SHA-256 of the read-only inputs, the output-directory guard, snapshot loading and the one-world build.

Nothing here writes under the Part T run directory or Part Q's directory; ``fs_manifest`` before and after is the evidence (section 3, section 11)."""

import hashlib
import sys
from pathlib import Path
from typing import Any

from studies.p10s2.memory import MemoryArm


class D0Refused(RuntimeError):
    """An engineering stop of D0: nothing further is computed or read."""


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fs_manifest(root: Path) -> dict[str, str]:
    """Every file under ``root`` (relative POSIX path) with its SHA-256, sorted by path. Symlinks are listed by their target's content when it is a file."""
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[p.relative_to(root).as_posix()] = _sha(p)
    return out


def manifest_diff(before: dict[str, str], after: dict[str, str]) -> dict[str, list[str]]:
    return {
        "added": sorted(set(after) - set(before)),
        "removed": sorted(set(before) - set(after)),
        "changed": sorted(k for k in set(before) & set(after) if before[k] != after[k]),
    }


def require_new_output_dir(out: Path, part_t_run_dir: Path) -> Path:
    """The output directory is new (never reused) and never inside the Part T run directory."""
    o, pt = out.resolve(), part_t_run_dir.resolve()
    if o == pt or pt in o.parents:
        raise D0Refused(f"refused: {out} is inside the Part T run directory {part_t_run_dir}")
    if out.exists():
        raise D0Refused(f"refused: {out} exists: D0 never reuses an output directory (stop and report)")
    out.mkdir(parents=True)
    return out


def load_cell(world: Any, r: int, order: str, snapshots: Path) -> dict[str, MemoryArm]:
    """The three M-append-related snapshots of one cell, hash-checked by the registered loader (``studies.p10is2.engine.load_t`` -> ``studies.p10s2.world.load_arm``): M1, M-append at the append point, M-append final."""
    from studies.p10is2 import engine

    names = {"M1": f"r{r}/M1/{order}", "append": f"r{r}/M-append/{order}@append", "final": f"r{r}/M-append/{order}"}
    arms = {k: engine.load_t(world, r, snapshots, n) for k, n in names.items()}
    for k, a in arms.items():
        if not isinstance(a, MemoryArm):
            raise D0Refused(f"snapshot {names[k]} is not a memory arm")
    return arms  # type: ignore[return-value]


def imported_module_hashes(repo: Path) -> dict[str, str]:
    """SHA-256 of every imported module file under the repository's ``studies`` and ``src`` trees (the frozen modules D0 imports), by repository-relative path."""
    out: dict[str, str] = {}
    root = repo.resolve()
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if not f:
            continue
        p = Path(f).resolve()
        if root in p.parents and p.suffix == ".py" and (p.relative_to(root).parts[0] in ("studies", "src")):
            out[p.relative_to(root).as_posix()] = _sha(p)
    return dict(sorted(out.items()))
